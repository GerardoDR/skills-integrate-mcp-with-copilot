"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import os
import re
import secrets
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path

from auth import Account, authenticate_account, create_account, get_account

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", secrets.token_urlsafe(32)),
    session_cookie="school_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=12, max_length=128)


class AccountRequest(Credentials):
    role: Literal["student", "staff"]


def get_current_account(request: Request) -> Account | None:
    account_id = request.session.get("account_id")
    if account_id is None:
        return None
    account = get_account(account_id)
    if account is None:
        request.session.clear()
    return account


def require_account(account: Account | None = Depends(get_current_account)) -> Account:
    if account is None:
        raise HTTPException(status_code=401, detail="Sign in is required")
    return account


def require_student(account: Account = Depends(require_account)) -> Account:
    if account.role != "student":
        raise HTTPException(status_code=403, detail="Only students can sign up for activities")
    return account


def require_staff(account: Account = Depends(require_account)) -> Account:
    if account.role not in {"staff", "admin"}:
        raise HTTPException(status_code=403, detail="Staff access is required")
    return account


def valid_email(email: str) -> bool:
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is not None


@app.post("/auth/login")
def login(credentials: Credentials, request: Request):
    if not valid_email(credentials.email):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    account = authenticate_account(credentials.email, credentials.password)
    if account is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    request.session["account_id"] = account.id
    return {"email": account.email, "role": account.role}


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Signed out"}


@app.get("/auth/me")
def get_session(account: Account | None = Depends(get_current_account)):
    if account is None:
        return {"authenticated": False}
    return {"authenticated": True, "email": account.email, "role": account.role}


@app.post("/admin/accounts", status_code=201)
def add_account(
    account_request: AccountRequest,
    account: Account = Depends(require_account),
):
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required")
    if not valid_email(account_request.email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    try:
        account = create_account(
            account_request.email, account_request.password, account_request.role
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"email": account.email, "role": account.role}


@app.get("/activities")
def get_activities(account: Account | None = Depends(get_current_account)):
    visible_activities = {}
    for name, activity in activities.items():
        details = {key: value for key, value in activity.items() if key != "participants"}
        details["participant_count"] = len(activity["participants"])
        if account is not None and account.role in {"staff", "admin"}:
            details["participants"] = list(activity["participants"])
        elif account is not None and account.role == "student":
            details["is_registered"] = account.email in activity["participants"]
        visible_activities[name] = details
    return visible_activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, account: Account = Depends(require_student)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if account.email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(account.email)
    return {"message": f"Signed up {account.email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str | None = None,
    account: Account = Depends(require_account),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]
    if account.role == "student":
        if email is not None and email.strip().lower() != account.email:
            raise HTTPException(status_code=403, detail="Students can only cancel their own signup")
        email = account.email
    elif account.role in {"staff", "admin"} and email is None:
        raise HTTPException(status_code=400, detail="Provide the participant email to remove")

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
