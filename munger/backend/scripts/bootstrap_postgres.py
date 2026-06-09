#!/usr/bin/env python3
"""One-shot Postgres bootstrap for Munger (role + database)."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse, urlunparse

import psycopg
from psycopg import sql


def _app_url(admin_url: str, app_user: str, app_password: str, app_db: str) -> str:
    parsed = urlparse(admin_url)
    netloc = parsed.hostname or "localhost"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if app_user and app_password:
        netloc = f"{app_user}:{app_password}@{netloc}"
    elif app_user:
        netloc = f"{app_user}@{netloc}"
    return urlunparse((parsed.scheme, netloc, f"/{app_db}", "", "", ""))


def main() -> int:
    admin_url = os.environ.get(
        "MUNGER_POSTGRES_ADMIN_URL",
        "postgresql://dbuser_dba:DBUser.DBA@host.docker.internal:5432/postgres",
    )
    app_user = os.environ.get("MUNGER_POSTGRES_APP_USER", "munger_app")
    app_password = os.environ.get("MUNGER_DB_PASSWORD", "Munger.App.2026")
    app_db = os.environ.get("MUNGER_POSTGRES_APP_DB", "munger")

    try:
        conn_ctx = psycopg.connect(admin_url, autocommit=True)
    except psycopg.OperationalError as exc:
        print(
            "Failed to connect to Postgres for bootstrap.\n"
            f"  URL host: {urlparse(admin_url).hostname}\n"
            "  Check MUNGER_POSTGRES_ADMIN_URL in munger/.env.\n"
            "  Pigsty admin password: docker exec pigsty grep pg_admin_password /root/pigsty/pigsty.yml",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    with conn_ctx as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(app_user),
                        sql.Literal(app_password),
                    )
                )
                print(f"Created role {app_user}")
            else:
                print(f"Role {app_user} already exists")

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (app_db,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {}").format(
                        sql.Identifier(app_db),
                        sql.Identifier(app_user),
                    )
                )
                print(f"Created database {app_db}")
            else:
                print(f"Database {app_db} already exists")

    parsed_admin = urlparse(admin_url)
    admin_db_url = urlunparse(
        (parsed_admin.scheme, parsed_admin.netloc, f"/{app_db}", "", "", "")
    )
    with psycopg.connect(admin_db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print(f"Ensured pgvector extension on database {app_db}")

    app_url = _app_url(admin_url, app_user, app_password, app_db)
    with psycopg.connect(app_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("GRANT ALL ON SCHEMA public TO {}").format(
                    sql.Identifier(app_user)
                )
            )
            print(f"Granted schema privileges to {app_user}")

    print("Postgres bootstrap complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
