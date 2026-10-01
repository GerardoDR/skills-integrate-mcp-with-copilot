import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
from contextlib import contextmanager


AUTH_DATABASE_PATH = Path(
    os.environ.get(
        "AUTH_DATABASE_PATH",
        str(Path(__file__).with_name("accounts.sqlite")),
    )
)


@dataclass(frozen=True)
class Account:
    id: int
    email: str
    role: str


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    AUTH_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)


def init_auth_store() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('student', 'staff', 'admin')),
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL
            )
            """
        )

    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if bool(admin_email) != bool(admin_password):
        raise RuntimeError("Set both ADMIN_EMAIL and ADMIN_PASSWORD to provision the initial admin.")
    if admin_email and admin_password:
        if len(admin_password) < 12:
            raise RuntimeError("ADMIN_PASSWORD must contain at least 12 characters.")
        if get_account_by_email(admin_email) is None:
            create_account(admin_email, admin_password, "admin")


def create_account(email: str, password: str, role: str) -> Account:
    normalized_email = email.strip().lower()
    if role not in {"student", "staff", "admin"}:
        raise ValueError("Invalid account role")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")

    salt = secrets.token_bytes(16)
    password_hash = _password_digest(password, salt)
    try:
        with _connect() as connection:
            cursor = connection.execute(
                "INSERT INTO accounts (email, role, password_salt, password_hash) VALUES (?, ?, ?, ?)",
                (normalized_email, role, salt, password_hash),
            )
            account_id = cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise ValueError("An account with this email already exists") from error
    return Account(id=account_id, email=normalized_email, role=role)


def authenticate_account(email: str, password: str) -> Account | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, email, role, password_salt, password_hash FROM accounts WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()

    if row is None:
        return None
    candidate = _password_digest(password, row["password_salt"])
    if not hmac.compare_digest(candidate, row["password_hash"]):
        return None
    return Account(id=row["id"], email=row["email"], role=row["role"])


def get_account(account_id: int) -> Account | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, email, role FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
    if row is None:
        return None
    return Account(id=row["id"], email=row["email"], role=row["role"])


def get_account_by_email(email: str) -> Account | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, email, role FROM accounts WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None:
        return None
    return Account(id=row["id"], email=row["email"], role=row["role"])


init_auth_store()