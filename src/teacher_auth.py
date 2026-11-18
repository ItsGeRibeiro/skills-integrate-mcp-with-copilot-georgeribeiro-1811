import argparse
import json
import os
import secrets
from getpass import getpass
from hashlib import scrypt
from pathlib import Path
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

router = APIRouter(prefix="/auth")
CREDENTIALS_FILE = Path(__file__).with_name("teachers.local.json")
COOKIE_NAME = "teacher_session"
SESSION_SECONDS = 8 * 60 * 60
sessions: dict[str, float] = {}


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


def password_hash(password: str, salt: bytes) -> bytes:
    return scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)


def verify_credentials(credentials: Credentials) -> bool:
    try:
        accounts = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(503, "Teacher accounts have not been configured") from exc

    account = accounts.get(credentials.username)
    salt = bytes.fromhex(account["salt"]) if account else bytes(16)
    expected = bytes.fromhex(account["hash"]) if account else bytes(64)
    matches = secrets.compare_digest(password_hash(credentials.password, salt), expected)
    return account is not None and matches


async def require_teacher(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME, "")
    expires = sessions.get(token)
    if expires is None or expires <= monotonic():
        sessions.pop(token, None)
        raise HTTPException(401, "Please log in as a teacher")


async def require_action_header(request: Request) -> None:
    # A cross-origin browser request cannot send this header without CORS approval.
    if request.headers.get("X-Teacher-Action") != "1":
        raise HTTPException(403, "Missing teacher action header")


@router.post("/login", dependencies=[Depends(require_action_header)])
async def login(credentials: Credentials, request: Request, response: Response):
    if not await run_in_threadpool(verify_credentials, credentials):
        raise HTTPException(401, "Invalid username or password")

    now = monotonic()
    for token, expires in list(sessions.items()):
        if expires <= now:
            del sessions[token]
    sessions.pop(request.cookies.get(COOKIE_NAME, ""), None)

    token = secrets.token_urlsafe(32)
    sessions[token] = now + SESSION_SECONDS
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
        secure=request.url.scheme == "https", samesite="strict",
    )
    return {"authenticated": True}


@router.get("/session", dependencies=[Depends(require_teacher)])
async def session(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True}


@router.post("/logout", status_code=204, dependencies=[Depends(require_action_header)])
async def logout(request: Request):
    sessions.pop(request.cookies.get(COOKIE_NAME, ""), None)
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_NAME, httponly=True, secure=request.url.scheme == "https", samesite="strict",
    )
    return response


def provision_account() -> None:
    parser = argparse.ArgumentParser(description="Provision a local teacher account.")
    parser.add_argument("username")
    username = parser.parse_args().username
    if not 1 <= len(username) <= 128:
        parser.error("The username must contain between 1 and 128 characters.")

    password = getpass("Teacher password: ")
    if not 12 <= len(password) <= 256:
        parser.error("The password must contain between 12 and 256 characters.")
    if password != getpass("Confirm password: "):
        parser.error("The passwords do not match.")

    try:
        accounts = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        accounts = {}
    salt = secrets.token_bytes(16)
    accounts[username] = {"salt": salt.hex(), "hash": password_hash(password, salt).hex()}
    fd = os.open(CREDENTIALS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(accounts, file, indent=2)
    print(f"Account saved for {username}.")


if __name__ == "__main__":
    provision_account()
