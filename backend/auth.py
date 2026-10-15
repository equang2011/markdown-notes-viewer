"""Optional PIN lock for the whole site.

Set SITE_PASSWORD (digits only, e.g. 6) to turn it on; unset leaves the site
open, e.g. for local dev. A correct PIN sets a session cookie. The built
frontend is served publicly so it can draw the lock screen; the data routes
(/notes, /tags) are what the cookie protects.
"""

import hashlib
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "")

COOKIE_NAME = "notes_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
PROTECTED_PREFIXES = ("/notes", "/tags")

# A PIN is easy to guess, so slow guessing down: after MAX_FAILURES wrong tries
# an address is locked out for LOCKOUT_SECONDS. In memory, so a restart resets
# it — fine for one instance.
MAX_FAILURES = 5
LOCKOUT_SECONDS = 60
_failures: dict[str, tuple[int, float]] = {}  # ip -> (count, locked_until)

# Derived from the PIN, so changing SITE_PASSWORD signs everyone out.
SESSION_TOKEN = (
    hmac.new(SITE_PASSWORD.encode(), b"notes-session", hashlib.sha256).hexdigest()
    if SITE_PASSWORD
    else ""
)

router = APIRouter(prefix="/auth")


def _is_authed(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME, "")
    return hmac.compare_digest(cookie.encode(), SESSION_TOKEN.encode())


def _client_ip(request: Request) -> str:
    # Railway's proxy appends the real client address as the last entry; earlier
    # entries can be forged by the client.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


async def require_session(request: Request, call_next):
    if (
        not SITE_PASSWORD
        or request.method == "OPTIONS"
        or not request.url.path.startswith(PROTECTED_PREFIXES)
        or _is_authed(request)
    ):
        return await call_next(request)
    return JSONResponse({"detail": "Locked"}, status_code=401)


class LoginBody(BaseModel):
    pin: str


@router.get("/status")
async def status(request: Request):
    return {
        "required": bool(SITE_PASSWORD),
        "authed": not SITE_PASSWORD or _is_authed(request),
        "pin_length": len(SITE_PASSWORD),
    }


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response):
    if not SITE_PASSWORD:
        return {"ok": True}

    ip = _client_ip(request)
    count, locked_until = _failures.get(ip, (0, 0.0))
    now = time.time()
    if locked_until > now:
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {int(locked_until - now) + 1}s.",
        )

    if not hmac.compare_digest(body.pin.encode(), SITE_PASSWORD.encode()):
        count += 1
        if count >= MAX_FAILURES:
            _failures[ip] = (0, now + LOCKOUT_SECONDS)
        else:
            _failures[ip] = (count, 0.0)
        raise HTTPException(status_code=401, detail="Wrong PIN")

    _failures.pop(ip, None)
    response.set_cookie(
        COOKIE_NAME,
        SESSION_TOKEN,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.headers.get("x-forwarded-proto", request.url.scheme) == "https",
    )
    return {"ok": True}
