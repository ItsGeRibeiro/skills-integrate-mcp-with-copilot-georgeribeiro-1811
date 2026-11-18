import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from src import teacher_auth
from src.app import activities, app


class TeacherModeTests(unittest.TestCase):
    headers = {"X-Teacher-Action": "1"}
    credentials = {"username": "teacher-test", "password": "test fixture password"}
    signup = "/activities/Chess%20Club/signup"
    unregister = "/activities/Chess%20Club/unregister"

    def setUp(self):
        directory = Path(self.enterContext(TemporaryDirectory()))
        path = directory / "teachers.json"
        salt = b"\x00" * 16
        path.write_text(json.dumps({self.credentials["username"]: {
            "salt": salt.hex(),
            "hash": teacher_auth.password_hash(self.credentials["password"], salt).hex(),
        }}), encoding="utf-8")
        self.enterContext(patch.object(teacher_auth, "CREDENTIALS_FILE", path))
        self.enterContext(patch.object(teacher_auth, "sessions", {}))
        original = deepcopy(activities)
        self.addCleanup(activities.update, original)
        self.client = self.enterContext(TestClient(app, base_url="https://testserver"))

    def test_guest_can_view_participants_but_cannot_change_registrations(self):
        catalog = self.client.get("/activities")
        self.assertEqual(catalog.status_code, 200)
        participants = catalog.json()["Chess Club"]["participants"]
        response = self.client.delete(self.unregister, params={"email": participants[0]}, headers=self.headers)
        self.assertEqual(response.status_code, 401)
        response = self.client.post(self.signup, params={"email": "new@example.com"}, headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/activities").json()["Chess Club"]["participants"], participants)

    def test_teacher_can_manage_registrations_until_logout(self):
        response = self.client.post("/auth/login", json=self.credentials, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        token = self.client.cookies.get(teacher_auth.COOKIE_NAME)
        self.assertEqual(self.client.get("/auth/session").status_code, 200)

        params = {"email": "new@example.com"}
        self.assertEqual(self.client.post(self.signup, params=params).status_code, 403)
        self.assertEqual(self.client.post(self.signup, params=params, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post(self.signup, params=params, headers=self.headers).status_code, 400)
        self.assertEqual(self.client.delete(self.unregister, params=params, headers=self.headers).status_code, 200)

        self.assertEqual(self.client.post("/auth/logout", headers=self.headers).status_code, 204)
        self.client.cookies.set(teacher_auth.COOKIE_NAME, token)
        self.assertEqual(self.client.get("/auth/session").status_code, 401)

    def test_wrong_password_does_not_create_session(self):
        credentials = {**self.credentials, "password": "wrong password"}
        response = self.client.post("/auth/login", json=credentials, headers=self.headers)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("set-cookie", response.headers)
        self.assertEqual(self.client.get("/auth/session").status_code, 401)
