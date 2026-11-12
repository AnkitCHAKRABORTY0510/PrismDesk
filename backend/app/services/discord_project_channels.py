"""Private Discord channels, one per project.

The notification worker calls :func:`sync_project_channels` about once a
minute. It reconciles Discord with Prism Desk instead of reacting to
individual events, so project creation, membership changes, renames,
archiving and members linking or unlinking Discord are all picked up the
same way, and a failed Discord call is simply retried on the next pass.

- Active project without a channel: create a text channel named after the
  project. ``@everyone`` cannot see it; the bot can.
- Each active project member with a linked Discord account gets a member
  permission overwrite (see, post, react, use threads). Members who leave
  the project or unlink Discord lose it.
- Archived (or deleted) project: the channel is kept for its history but
  becomes read-only for members. A deleted project's channel row goes away
  with the project (ON DELETE CASCADE); the Discord channel itself is left
  for an admin to delete by hand.

What was last applied is stored in ``discord_project_channels`` so nothing
is sent to Discord when nothing changed.

Run one pass by hand (e.g. to backfill existing projects):

    python -m app.services.discord_project_channels
"""

import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import DiscordAccount, DiscordProjectChannel
from app.models.project import Project, ProjectMember

logger = logging.getLogger("prism.discord_channels")

# Discord permission bits.
ADD_REACTIONS = 1 << 6
VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
EMBED_LINKS = 1 << 14
ATTACH_FILES = 1 << 15
READ_MESSAGE_HISTORY = 1 << 16
CREATE_PUBLIC_THREADS = 1 << 35
SEND_MESSAGES_IN_THREADS = 1 << 38
MANAGE_CHANNELS = 1 << 4
MANAGE_ROLES = 1 << 28

POSTING = SEND_MESSAGES | SEND_MESSAGES_IN_THREADS | CREATE_PUBLIC_THREADS | ADD_REACTIONS | ATTACH_FILES | EMBED_LINKS
MEMBER_ALLOW = VIEW_CHANNEL | READ_MESSAGE_HISTORY | POSTING
READ_ONLY_ALLOW = VIEW_CHANNEL | READ_MESSAGE_HISTORY
BOT_ALLOW = MEMBER_ALLOW

# Everything the bot needs in the server (invite link / bot role).
BOT_GUILD_PERMISSIONS = BOT_ALLOW | MANAGE_CHANNELS | MANAGE_ROLES

MANAGED_STATUSES = ("active", "archived", "deleted")


def enabled() -> bool:
    return bool(settings.DISCORD_PROJECT_CHANNELS and settings.DISCORD_GUILD_ID and settings.discord_bot_configured)


def channel_name(title: str) -> str:
    """Discord-style channel name: lowercase words joined by hyphens."""

    slug = re.sub(r"[^\w]+", "-", title.lower(), flags=re.UNICODE).strip("-_")
    return (slug or "project")[:100]


def channel_for_project(db: Session, project_id) -> DiscordProjectChannel | None:
    """The project's channel row, or None.

    Runs in a SAVEPOINT so a database without this table yet (migration not
    applied) cannot break the caller's transaction, e.g. adding a paper.
    """

    try:
        with db.begin_nested():
            return db.get(DiscordProjectChannel, project_id)
    except SQLAlchemyError:
        logger.warning("discord_project_channels is unavailable; run the database migration.")
        return None


def _desired_members(db: Session, project_id) -> set[str]:
    return set(
        db.scalars(
            select(DiscordAccount.discord_user_id)
            .join(ProjectMember, ProjectMember.user_id == DiscordAccount.user_id)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.membership_status == "active",
                DiscordAccount.status == "linked",
            )
        ).all()
    )


def _mode(project: Project) -> str:
    return "active" if project.status == "active" else "read_only"


def _grant(sender, channel_id: str, discord_id: str, mode: str) -> bool:
    if mode == "active":
        result = sender.set_member_permissions(channel_id, discord_id, MEMBER_ALLOW)
    else:
        result = sender.set_member_permissions(channel_id, discord_id, READ_ONLY_ALLOW, POSTING)
    if not result.success:
        # Typically the person is not in the Discord server yet; retried next pass.
        logger.info("Could not give a member access to channel %s: %s", channel_id, result.error)
    return result.success


def _create(db: Session, sender, project: Project) -> DiscordProjectChannel | None:
    bot_id = sender.bot_user_id()
    if not bot_id:
        logger.warning("Could not look up the bot's Discord user; project channels skipped.")
        return None
    name = channel_name(project.title)
    overwrites = [
        # The @everyone role has the same ID as the server.
        {"id": settings.DISCORD_GUILD_ID, "type": 0, "allow": "0", "deny": str(VIEW_CHANNEL)},
        {"id": bot_id, "type": 1, "allow": str(BOT_ALLOW), "deny": "0"},
    ]
    result = sender.create_text_channel(
        settings.DISCORD_GUILD_ID,
        name,
        overwrites,
        parent_id=settings.DISCORD_PROJECT_CATEGORY_ID or None,
        topic=f"Private channel for the Prism Desk project “{project.title}”. New project papers are posted here.",
    )
    if not result.success or not result.channel_id:
        logger.warning("Could not create a Discord channel for project %s: %s", project.id, result.error)
        return None
    row = DiscordProjectChannel(project_id=project.id, channel_id=result.channel_id, channel_name=name)
    db.add(row)
    db.commit()
    logger.info("Created Discord channel #%s for project %s", name, project.id)
    return row


def sync_project(db: Session, sender, project: Project) -> None:
    row = channel_for_project(db, project.id)
    if row is None:
        if project.status != "active":
            return  # never create channels for archived projects
        row = _create(db, sender, project)
        if row is None:
            return

    name = channel_name(project.title)
    if row.channel_name != name:
        if sender.rename_channel(row.channel_id, name).success:
            row.channel_name = name

    mode = _mode(project)
    desired = _desired_members(db, project.id)
    applied = set(row.member_discord_ids or [])
    to_grant = desired if mode != row.access_mode else desired - applied

    for discord_id in sorted(to_grant):
        if _grant(sender, row.channel_id, discord_id, mode):
            applied.add(discord_id)
        else:
            applied.discard(discord_id)
    for discord_id in sorted(applied - desired):
        if sender.remove_member_permissions(row.channel_id, discord_id).success:
            applied.discard(discord_id)

    if mode != row.access_mode and desired <= applied:
        row.access_mode = mode
    if set(row.member_discord_ids or []) != applied:
        row.member_discord_ids = sorted(applied)
    db.commit()


def sync_project_channels(db: Session, sender) -> int:
    """One reconciliation pass over all projects. Returns projects visited."""

    if not enabled():
        return 0
    try:
        projects = db.scalars(select(Project).where(Project.status.in_(MANAGED_STATUSES))).all()
        db.scalar(select(DiscordProjectChannel.project_id).limit(1))  # table present?
    except SQLAlchemyError:
        db.rollback()
        logger.warning("discord_project_channels table is missing; run the database migration.")
        return 0
    for project in projects:
        try:
            sync_project(db, sender, project)
        except Exception:
            db.rollback()
            logger.exception("Discord channel sync failed for project %s; continuing.", project.id)
    return len(projects)


def main() -> None:  # pragma: no cover - manual backfill
    from sqlalchemy.orm import sessionmaker

    from app.core.logging import configure_logging
    from app.database.session import engine
    from app.services.discord_client import DiscordSender

    configure_logging()
    if not enabled():
        print("Project channels are off: set DISCORD_GUILD_ID and DISCORD_BOT_TOKEN (and DISCORD_PROJECT_CHANNELS=true).")
        return
    with sessionmaker(bind=engine, autoflush=False)() as db:
        visited = sync_project_channels(db, DiscordSender())
        channels = db.scalars(select(DiscordProjectChannel)).all()
        print(f"Checked {visited} projects; {len(channels)} have a Discord channel.")


if __name__ == "__main__":  # pragma: no cover
    main()
