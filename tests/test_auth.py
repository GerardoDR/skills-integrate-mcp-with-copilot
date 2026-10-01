import os
import sys
import tempfile
import unittest
from pathlib import Path


test_data = tempfile.TemporaryDirectory()
os.environ["AUTH_DATABASE_PATH"] = str(Path(test_data.name) / "accounts.sqlite")
os.environ["ADMIN_EMAIL"] = "admin@mergington.edu"
os.environ["ADMIN_PASSWORD"] = "admin-test-password"
os.environ["SESSION_SECRET"] = "test-session-secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

from app import activities, app


class RoleAccessTests(unittest.TestCase):
    def setUp(self):
        self.original_participants = {
            name: list(activity["participants"])
            for name, activity in activities.items()
        }
        self.client = TestClient(app)

    def tearDown(self):
        for name, participants in self.original_participants.items():
            activities[name]["participants"] = participants
        self.client.close()

    def _create_account(self, email, role):
        response = self.client.post(
            "/admin/accounts",
            json={"email": email, "password": "account-test-password", "role": role},
        )
        self.assertEqual(response.status_code, 201, response.text)

    def test_public_activity_list_does_not_expose_participant_emails(self):
        response = self.client.get("/activities")
        self.assertEqual(response.status_code, 200)
        activity = response.json()["Chess Club"]
        self.assertNotIn("participants", activity)
        self.assertEqual(activity["participant_count"], len(activities["Chess Club"]["participants"]))

    def test_anonymous_user_cannot_sign_up(self):
        response = self.client.post("/activities/Chess Club/signup")
        self.assertEqual(response.status_code, 401)

    def test_student_can_only_cancel_own_signup(self):
        self.client.post(
            "/auth/login",
            json={"email": "admin@mergington.edu", "password": "admin-test-password"},
        )
        student_email = "student-{}@mergington.edu".format(os.getpid())
        self._create_account(student_email, "student")
        activities["Chess Club"]["participants"].append("another-student@mergington.edu")

        student = TestClient(app)
        login = student.post(
            "/auth/login",
            json={"email": student_email, "password": "account-test-password"},
        )
        self.assertEqual(login.status_code, 200)
        response = student.delete(
            "/activities/Chess Club/unregister?email=another-student%40mergington.edu"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("another-student@mergington.edu", activities["Chess Club"]["participants"])
        student.close()

    def test_student_can_sign_up_and_cancel_their_own_signup(self):
        self.client.post(
            "/auth/login",
            json={"email": "admin@mergington.edu", "password": "admin-test-password"},
        )
        student_email = "signup-{}@mergington.edu".format(os.getpid())
        self._create_account(student_email, "student")

        student = TestClient(app)
        student.post(
            "/auth/login",
            json={"email": student_email, "password": "account-test-password"},
        )
        signup = student.post("/activities/Chess Club/signup")
        self.assertEqual(signup.status_code, 200, signup.text)
        unregister = student.delete("/activities/Chess Club/unregister")
        self.assertEqual(unregister.status_code, 200, unregister.text)
        self.assertNotIn(student_email, activities["Chess Club"]["participants"])
        student.close()

    def test_staff_can_view_roster(self):
        self.client.post(
            "/auth/login",
            json={"email": "admin@mergington.edu", "password": "admin-test-password"},
        )
        staff_email = "staff-{}@mergington.edu".format(os.getpid())
        self._create_account(staff_email, "staff")

        staff = TestClient(app)
        login = staff.post(
            "/auth/login",
            json={"email": staff_email, "password": "account-test-password"},
        )
        self.assertEqual(login.status_code, 200)
        response = staff.get("/activities")
        self.assertIn("participants", response.json()["Chess Club"])
        staff.close()


if __name__ == "__main__":
    unittest.main()