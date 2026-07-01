import asyncio

from sqlalchemy import text

from app.core.database import engine

SQL_MIGRATIONS = [
    # Blog lifecycle actor + timestamp columns
    ("approved_by_id",
     'ALTER TABLE blogs ADD COLUMN IF NOT EXISTS approved_by_id '
     'INTEGER REFERENCES "user"(id) ON DELETE SET NULL'),
    ("approved_at",
     'ALTER TABLE blogs ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ'),
    ("published_by_id",
     'ALTER TABLE blogs ADD COLUMN IF NOT EXISTS published_by_id '
     'INTEGER REFERENCES "user"(id) ON DELETE SET NULL'),
    ("published_at",
     'ALTER TABLE blogs ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ'),

    # Proper user_permissions table (replaces User Custom / Admin Custom hack)
    ("user_permissions_table", """
        CREATE TABLE IF NOT EXISTS user_permissions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            granted_by_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, permission_id)
        )
    """),
    ("up_idx_user",
     "CREATE INDEX IF NOT EXISTS ix_user_permissions_user_id ON user_permissions(user_id)"),
    ("up_idx_perm",
     "CREATE INDEX IF NOT EXISTS ix_user_permissions_permission_id ON user_permissions(permission_id)"),

    # Audit logs table
    ("audit_logs_table", """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            username VARCHAR NOT NULL,
            email VARCHAR,
            module VARCHAR NOT NULL,
            action_type VARCHAR NOT NULL,
            description TEXT NOT NULL,
            ip_address VARCHAR,
            status VARCHAR NOT NULL DEFAULT 'Success',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """),
    ("audit_logs_idx_action",
     "CREATE INDEX IF NOT EXISTS ix_audit_logs_action_type ON audit_logs(action_type)"),
    ("audit_logs_idx_module",
     "CREATE INDEX IF NOT EXISTS ix_audit_logs_module ON audit_logs(module)"),
    ("audit_logs_idx_ts",
     "CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)"),
]


async def main() -> None:
    async with engine.begin() as conn:
        for name, sql in SQL_MIGRATIONS:
            try:
                await conn.execute(text(sql))
                print(f"OK: {name}")
            except Exception as e:
                print(f"SKIP {name}: {e}")


asyncio.run(main())
