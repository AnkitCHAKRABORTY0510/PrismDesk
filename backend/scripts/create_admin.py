from datetime import datetime, timezone
from getpass import getpass
from pydantic import ValidationError

from sqlalchemy import select, func

from app.database.session import SessionLocal
from app.models.user import User
from app.models.role import Role
from app.core.security import hash_password
from app.schemas.auth import RegisterRequest


def create_admin():
    db = SessionLocal()

    try:
        # Check whether an administrator already exists.
        existing_admin = db.execute(
            select(User)
            .join(User.roles)
            .where(Role.name == "Administrator")
        ).scalar_one_or_none()

        if existing_admin:
            print("An administrator already exists.")
            return

        # Find the predefined administrator role.
        admin_role = db.execute(
            select(Role).where(Role.name == "Administrator")
        ).scalar_one_or_none()

        if not admin_role:
            print("Administrator role not found.")
            print("Run the role-seeding migration first.")
            return

        print("\n=== Prism Desk Administrator Setup ===\n")

        username = input("Username: ").strip()
        email = input("Email: ").strip()
        full_name = input("Full name: ").strip()

        password = getpass("Password (minimum 12 characters): ")
        confirm_password = getpass("Confirm password: ")

        if password != confirm_password:
            print("Passwords do not match.")
            return

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
            return

        # Validate registration information.
        try:
            validated = RegisterRequest(
                username=username,
                email=email,
                full_name=full_name,
                password=password,
            )
        except ValidationError as error:
            for item in error.errors(include_input=False):
                field = ".".join(str(part) for part in item["loc"])
                print(f"{field}: {item['msg']}")
            return

        # Check for duplicate username or email.
        duplicate = db.execute(
            select(User).where(
                (func.lower(User.username) == validated.username)
                | (func.lower(User.email) == str(validated.email))
            )
        ).scalar_one_or_none()

        if duplicate:
            print("Username or email is already registered.")
            return

        admin = User(
            username=validated.username,
            email=str(validated.email),
            full_name=validated.full_name,
            password_hash=hash_password(password),
            account_status="approved",
            approved_at=datetime.now(timezone.utc),
        )

        admin.roles.append(admin_role)

        db.add(admin)
        db.commit()

        print("\nAdministrator created successfully.")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print("Account status: approved")
        print("Role: Administrator")

    except Exception:
        db.rollback()
        print("\nAdministrator creation failed. Check the server logs.")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
