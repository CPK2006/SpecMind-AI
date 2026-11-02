"""Add nullable project ownership and ensure the auth schema exists.

Revision ID: c7d8e9f0a1b2
Revises: a8f3c1d2e4b6
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "a8f3c1d2e4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OWNERSHIP_FK = "fk_projects_user_id_users_a8f3c1d2e4b6"


def _columns(inspector, table_name: str) -> dict:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def _is_uuid(column) -> bool:
    return isinstance(column["type"], sa.Uuid)


def _available_email_index_name(bind) -> str:
    """Choose an unused index name in the active schema."""
    existing_names = set(
        bind.execute(
            sa.text(
                "SELECT indexname FROM pg_catalog.pg_indexes "
                "WHERE schemaname = current_schema()"
            )
        ).scalars()
    )
    base_name = "ix_users_email"
    if base_name not in existing_names:
        return base_name

    candidate = f"{base_name}_c7d8e9f0a1b2"
    suffix = 1
    while candidate in existing_names:
        candidate = f"{base_name}_c7d8e9f0a1b2_{suffix}"
        suffix += 1
    return candidate


def _ensure_users_table(bind, inspector) -> None:
    if "users" not in inspector.get_table_names():
        email_index_name = _available_email_index_name(bind)
        op.create_table(
            "users",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("hashed_password", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(email_index_name, "users", ["email"], unique=True)
        return

    columns = _columns(inspector, "users")
    expected_columns = {"id", "email", "full_name", "hashed_password", "created_at"}
    missing_columns = expected_columns - columns.keys()
    if missing_columns:
        raise RuntimeError(
            "The existing users table is missing required columns: "
            + ", ".join(sorted(missing_columns))
            + ". Refusing to alter existing user data automatically."
        )
    if not _is_uuid(columns["id"]):
        raise RuntimeError("users.id must use a UUID type before project ownership can be added.")

    has_unique_email = any(
        index.get("unique") and index.get("column_names") == ["email"]
        for index in inspector.get_indexes("users")
    ) or any(
        constraint.get("column_names") == ["email"]
        for constraint in inspector.get_unique_constraints("users")
    )
    if not has_unique_email:
        duplicate_count = bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM ("
                "SELECT email FROM users GROUP BY email HAVING COUNT(*) > 1"
                ") AS duplicate_emails"
            )
        ).scalar_one()
        if duplicate_count:
            raise RuntimeError(
                "Cannot add the unique users.email index: duplicate email values exist. "
                "Resolve duplicates before retrying this migration."
            )
        email_index_name = _available_email_index_name(bind)
        op.create_index(email_index_name, "users", ["email"], unique=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "projects" not in inspector.get_table_names():
        raise RuntimeError(
            "The projects table does not exist. Apply the existing project migrations first."
        )

    _ensure_users_table(bind, inspector)

    inspector = inspect(bind)
    project_columns = _columns(inspector, "projects")
    if "id" not in project_columns or not _is_uuid(project_columns["id"]):
        raise RuntimeError("projects.id must use a UUID type before project ownership can be added.")

    if "user_id" not in project_columns:
        op.add_column(
            "projects",
            sa.Column("user_id", sa.Uuid(), nullable=True),
        )
        inspector = inspect(bind)
        project_columns = _columns(inspector, "projects")
    elif not _is_uuid(project_columns["user_id"]):
        raise RuntimeError("projects.user_id must use a UUID type; refusing an implicit type conversion.")

    if not _is_uuid(_columns(inspector, "users")["id"]):
        raise RuntimeError("users.id must use a UUID type before project ownership can be added.")

    orphan_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM projects AS p "
            "LEFT JOIN users AS u ON u.id = p.user_id "
            "WHERE p.user_id IS NOT NULL AND u.id IS NULL"
        )
    ).scalar_one()
    if orphan_count:
        raise RuntimeError(
            "Cannot add the projects.user_id foreign key: "
            f"{orphan_count} non-null ownership value(s) have no matching user. "
            "No ownership values were changed. Resolve these references and retry."
        )

    if project_columns["user_id"]["nullable"] is False:
        op.alter_column(
            "projects",
            "user_id",
            existing_type=project_columns["user_id"]["type"],
            nullable=True,
        )

    foreign_keys = inspector.get_foreign_keys("projects")
    ownership_foreign_keys = [
        foreign_key
        for foreign_key in foreign_keys
        if "user_id" in (foreign_key.get("constrained_columns") or [])
    ]
    constraint_names = {foreign_key.get("name") for foreign_key in foreign_keys}
    constraint_names.add(inspector.get_pk_constraint("projects").get("name"))
    constraint_names.update(
        constraint.get("name")
        for constraint in inspector.get_unique_constraints("projects")
    )
    constraint_names.update(
        constraint.get("name")
        for constraint in inspector.get_check_constraints("projects")
    )
    if OWNERSHIP_FK in constraint_names:
        raise RuntimeError(
            f"Constraint name {OWNERSHIP_FK!r} is already in use. "
            "Resolve the schema conflict before retrying this migration."
        )
    if any(
        foreign_key.get("referred_table") != "users"
        or foreign_key.get("referred_columns") != ["id"]
        for foreign_key in ownership_foreign_keys
    ):
        raise RuntimeError(
            "projects.user_id already has a foreign key to a different target. "
            "Resolve the schema conflict before retrying this migration."
        )

    has_ownership_foreign_key = bool(ownership_foreign_keys)
    if not has_ownership_foreign_key:
        op.create_foreign_key(
            OWNERSHIP_FK,
            "projects",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Remove the ownership constraint without discarding user/project data.

    The users table and nullable projects.user_id column are retained because
    they may predate this migration or contain data written after its upgrade.
    """
    inspector = inspect(op.get_bind())
    if "projects" not in inspector.get_table_names():
        return

    for foreign_key in inspector.get_foreign_keys("projects"):
        if (
            foreign_key.get("name") == OWNERSHIP_FK
            and foreign_key.get("constrained_columns") == ["user_id"]
            and foreign_key.get("referred_table") == "users"
            and foreign_key.get("referred_columns") == ["id"]
        ):
            op.drop_constraint(OWNERSHIP_FK, "projects", type_="foreignkey")
            break
