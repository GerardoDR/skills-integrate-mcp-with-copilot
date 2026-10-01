# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities with a student account
- Staff and administrators can view participant rosters
- Administrators can create student and staff accounts
- Public activity listings show participant counts, not email addresses

Accounts use SQLite and passwords are stored as scrypt hashes. Students and staff
accounts are provisioned by an administrator. Configure `ADMIN_EMAIL`,
`ADMIN_PASSWORD` (at least 12 characters), and a stable `SESSION_SECRET` before
starting the app. Set `COOKIE_SECURE=true` when serving over HTTPS. The initial
administrator is created on first startup when those credentials are supplied.

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | List activities; participant emails are visible only to staff      |
| POST   | `/auth/login`                                                      | Sign in and start a role-based session                               |
| POST   | `/auth/logout`                                                     | End the current session                                              |
| GET    | `/auth/me`                                                         | Get the current account and role                                     |
| POST   | `/admin/accounts`                                                  | Create a student or staff account (admin only)                       |
| POST   | `/activities/{activity_name}/signup`                               | Sign up the authenticated student                                   |
| DELETE | `/activities/{activity_name}/unregister`                           | Cancel your signup; staff may supply a participant email             |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data is still stored in memory and resets when the server restarts.
Account data is stored in `src/accounts.sqlite`.
