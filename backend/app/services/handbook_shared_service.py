"""Handbook shared notes: one note per student per day, written for supervisors.

Who can read a student's shared notes follows the handbook-entry rule: the
student, and anyone who manages (owner/supervisor role, or Administrator) a
non-deleted project where the student is an active owner or member.
Commenting needs such a project to be *active*, as for entries. The private
``DailySummary`` journal is a different table and is never touched here.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import has_capability
from app.models.handbook import HandbookSharedNote, HandbookSharedNoteComment, HandbookSharedNoteVersion
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.schemas.admin import user_summary
from app.schemas.common import PageParams, paginate
from app.schemas.handbook_shared import (
    SharedCommentResponse,
    SharedNoteCreate,
    SharedNoteResponse,
    SharedNoteUpdate,
)
from app.services.audit_service import record_audit
from app.services.handbook_service import _check_date, _commit
from app.services.notification_service import enqueue_notification
from app.services.project_access import managed_project_ids


def _supervised_students(user: User, active_only: bool = False):
    """Subquery of user ids whose shared notes ``user`` may read (or comment on)."""

    statement = (
        select(ProjectMember.user_id)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            ProjectMember.project_id.in_(managed_project_ids(user)),
            ProjectMember.membership_status == "active",
            ProjectMember.membership_role.in_(("owner", "member")),
        )
    )
    if active_only:
        statement = statement.where(Project.status == "active")
    return statement


def _can_comment(db: Session, user: User, note: HandbookSharedNote) -> bool:
    if note.student_id == user.id:
        return False
    return note.student_id in set(db.scalars(_supervised_students(user, active_only=True)).all())


def _visible_note(db: Session, user: User, note_id: UUID) -> HandbookSharedNote:
    note = db.scalar(
        select(HandbookSharedNote)
        .options(selectinload(HandbookSharedNote.student))
        .where(
            HandbookSharedNote.id == note_id,
            or_(
                HandbookSharedNote.student_id == user.id,
                HandbookSharedNote.student_id.in_(_supervised_students(user)),
            ),
        )
    )
    if note is None:
        raise NotFoundError("Shared note not found.")
    return note


def _snapshot(note: HandbookSharedNote) -> dict:
    return {"body": note.body}


def create_note(db: Session, user: User, data: SharedNoteCreate) -> HandbookSharedNote:
    if not has_capability(user.role_names, "handbook.write"):
        raise ForbiddenError("Only students write shared notes.")
    _check_date(data.entry_date)
    note = HandbookSharedNote(student_id=user.id, entry_date=data.entry_date, body=data.body)
    db.add(note)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("You already have a shared note for this date. Edit it instead.")
    db.add(HandbookSharedNoteVersion(note_id=note.id, version=1, snapshot=_snapshot(note)))
    _commit(db)
    db.refresh(note)
    return note


def update_note(db: Session, user: User, note_id: UUID, data: SharedNoteUpdate) -> HandbookSharedNote:
    note = _visible_note(db, user, note_id)
    if note.student_id != user.id:
        raise ForbiddenError("Only the author can edit a shared note.")
    if data.body == note.body:
        return note
    note.body = data.body
    note.version += 1
    db.add(HandbookSharedNoteVersion(note_id=note.id, version=note.version, snapshot=_snapshot(note)))
    _commit(db)
    db.refresh(note)
    return note


def get_note(db: Session, user: User, note_id: UUID) -> HandbookSharedNote:
    return _visible_note(db, user, note_id)


def list_notes(
    db: Session,
    user: User,
    params: PageParams,
    date_from: date | None,
    date_to: date | None,
    student_id: UUID | None,
):
    statement = (
        select(HandbookSharedNote)
        .options(selectinload(HandbookSharedNote.student))
        .where(
            or_(
                HandbookSharedNote.student_id == user.id,
                HandbookSharedNote.student_id.in_(_supervised_students(user)),
            )
        )
        .order_by(HandbookSharedNote.entry_date.desc(), HandbookSharedNote.created_at.desc())
    )
    if date_from:
        statement = statement.where(HandbookSharedNote.entry_date >= date_from)
    if date_to:
        statement = statement.where(HandbookSharedNote.entry_date <= date_to)
    if student_id:
        statement = statement.where(HandbookSharedNote.student_id == student_id)
    return paginate(db, statement, params)


def note_versions(db: Session, user: User, note_id: UUID) -> list[HandbookSharedNoteVersion]:
    _visible_note(db, user, note_id)
    return list(
        db.scalars(
            select(HandbookSharedNoteVersion)
            .where(HandbookSharedNoteVersion.note_id == note_id)
            .order_by(HandbookSharedNoteVersion.version.desc())
        ).all()
    )


def _comment_tree(comments: list[HandbookSharedNoteComment]) -> list[SharedCommentResponse]:
    nodes = {
        c.id: SharedCommentResponse(
            id=c.id,
            note_id=c.note_id,
            parent_id=c.parent_id,
            author=user_summary(c.author) if c.author else None,
            body=c.body,
            created_at=c.created_at,
        )
        for c in comments
    }
    roots = []
    for comment in comments:
        node = nodes[comment.id]
        if comment.parent_id and comment.parent_id in nodes:
            nodes[comment.parent_id].replies.append(node)
        else:
            roots.append(node)
    return roots


def note_responses(
    db: Session, user: User, notes: list[HandbookSharedNote], with_comments: bool = False
) -> list[SharedNoteResponse]:
    if not notes:
        return []
    ids = [note.id for note in notes]
    counts = dict(
        db.execute(
            select(HandbookSharedNoteComment.note_id, func.count())
            .where(HandbookSharedNoteComment.note_id.in_(ids))
            .group_by(HandbookSharedNoteComment.note_id)
        ).all()
    )
    commentable = set(db.scalars(_supervised_students(user, active_only=True)).all())
    by_note: dict[UUID, list[HandbookSharedNoteComment]] = {}
    if with_comments:
        for comment in db.scalars(
            select(HandbookSharedNoteComment)
            .options(selectinload(HandbookSharedNoteComment.author))
            .where(HandbookSharedNoteComment.note_id.in_(ids))
            .order_by(HandbookSharedNoteComment.created_at)
        ).all():
            by_note.setdefault(comment.note_id, []).append(comment)
    return [
        SharedNoteResponse(
            id=note.id,
            student=user_summary(note.student),
            entry_date=note.entry_date,
            body=note.body,
            version=note.version,
            created_at=note.created_at,
            updated_at=note.updated_at,
            comment_count=counts.get(note.id, 0),
            comments=_comment_tree(by_note.get(note.id, [])),
            can_edit=note.student_id == user.id,
            # Supervisors start threads; the author can reply (checked on post).
            can_comment=note.student_id in commentable and note.student_id != user.id,
        )
        for note in notes
    ]


def add_comment(db: Session, user: User, note_id: UUID, body: str, parent_id: UUID | None) -> HandbookSharedNoteComment:
    note = _visible_note(db, user, note_id)
    is_author = note.student_id == user.id
    supervisor = _can_comment(db, user, note)

    parent = None
    if parent_id:
        parent = db.get(HandbookSharedNoteComment, parent_id)
        if not parent or parent.note_id != note.id:
            raise NotFoundError("Comment not found.")
        if parent.parent_id is not None:
            raise BadRequestError("Replies can only be added to top-level comments.")
        if not (is_author or supervisor):
            raise ForbiddenError("You cannot reply here.")
    elif not supervisor:
        raise ForbiddenError("Only the student's supervisors can comment on shared notes.")

    comment = HandbookSharedNoteComment(note_id=note.id, parent_id=parent_id, author_id=user.id, body=body.strip())
    db.add(comment)
    db.flush()
    record_audit(
        db,
        user.id,
        "handbook.shared_reply_added" if parent else "handbook.shared_comment_added",
        "handbook_shared_note",
        note.id,
        {"comment_id": comment.id},
    )

    recipients = {note.student_id}
    if parent is not None and parent.author_id:
        recipients.add(parent.author_id)
    recipients.discard(user.id)
    for recipient_id in recipients:
        enqueue_notification(
            db,
            recipient_id=recipient_id,
            category="handbook",
            event_type="handbook.shared_comment_added",
            title="New comment on a shared handbook note",
            body=f"{user.full_name} commented on the {note.entry_date.isoformat()} shared note.",
            entity_type="handbook_shared_note",
            entity_id=note.id,
            dedupe_key=f"handbook.shared_comment:{comment.id}:{recipient_id}",
        )
    _commit(db)
    db.refresh(comment)
    return comment
