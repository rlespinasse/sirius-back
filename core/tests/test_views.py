from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.models import ChallengeStat
from core.tests.factories import TestFactory


class APITests(APITestCase, TestFactory):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        self.user = User.objects.create_user(username="testuser", password="test_pass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_1)

    def test_get_challenge_success(self):
        url = f"/api/get-challenge-by-id/{self.challenge_1.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": self.challenge_1.id,
                "name": self.challenge_1.name,
                "text": self.challenge_1.text,
                "level": self.challenge_1.level,
                "course": self.course_1.id,
                "estimated_minutes": self.challenge_1.estimated_minutes,
                "is_active": self.challenge_1.is_active,
                "verified": self.challenge_1.verified,
                "created_at": self.challenge_1.created_at.isoformat().replace(
                    "+00:00", "Z"
                ),
                "updated_at": self.challenge_1.updated_at.isoformat().replace(
                    "+00:00", "Z"
                ),
            },
        )

    def test_get_challenge_not_found(self):
        url = "/api/get-challenge-by-id/9999/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Challenge not found.")

    @patch("core.views.ChallengeService.get_challenge")
    def test_generate_challenge(self, mock_get_challenge):
        mock_get_challenge.return_value = {
            "challenge_id": 1,
            "challenge": "Mocked challenge",
        }
        url = reverse("get-challenge")
        self.client.login(username="user_t1", password="pwd1")
        data = {"course_id": self.course_1.id}
        response = self.client.post(url, data)
        mock_get_challenge.assert_called_once_with(self.student_1.id, self.course_1.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("challenge", response.data)
        self.assertEqual(response.data["challenge"], "Mocked challenge")

    @patch("core.views.ChallengeService.get_feedback")
    def test_generate_feedback_with_text(self, mock_get_feedback):
        mock_get_feedback.return_value = "Mocked feedback"
        url = reverse("get-feedback")
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "answer_type": "text",
            "answer_text": "This is my answer.",
        }
        response = self.client.post(url, data)
        mock_get_feedback.assert_called_once_with(
            self.student_1.id, self.challenge_1.id, "text", "This is my answer.", None
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("feedback", response.data)

    @patch("core.views.ChallengeService.get_feedback")
    def test_generate_feedback_with_audio(self, mock_get_feedback):
        mock_get_feedback.return_value = "Mocked feedback"
        temp_file = SimpleUploadedFile(
            "test_audio.mp3", b"Audio content", content_type="audio/mpeg"
        )
        url = reverse("get-feedback")
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "answer_type": "audio",
            "answer_audio": temp_file,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("feedback", response.data)

    @patch("core.views.ChallengeService.get_feedback")
    def test_generate_feedback_failed(self, mock_get_feedback):
        mock_get_feedback.return_value = None
        url = reverse("get-feedback")
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "answer_type": "text",
            "answer_text": "This is my answer.",
            "moment": 1,
        }
        response = self.client.post(url, data)
        mock_get_feedback.assert_called_once_with(
            self.student_1.id, self.challenge_1.id, "text", "This is my answer.", 1
        )
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)

    @patch("core.views.ChallengeService.get_feedback")
    def test_generate_feedback_invalid_type(self, mock_get_feedback):
        mock_get_feedback.return_value = None
        url = reverse("get-feedback")
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "answer_type": "9999",
            "answer_text": "This is my answer.",
        }
        response = self.client.post(url, data)
        mock_get_feedback.assert_not_called()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_course_summary_with_no_courses(self):
        self.student_1.challenges.add(self.challenge_1)
        self.student_1.challenges.add(self.challenge_2)
        self.student_1.challenges.add(self.challenge_3)
        total_courses = 2
        url = reverse("course-summary")
        self.client.login(username="user_t1", password="pwd1")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), total_courses)
        self.assertEqual(
            response.data[0]["course__id"], self.course_1.id, self.course_1.id
        )
        self.assertEqual(
            response.data[0]["course__title"], self.course_1.title, self.course_1.title
        )
        self.assertEqual(response.data[0]["total_challenges"], 2)
        self.assertEqual(
            response.data[1]["course__id"], self.course_2.id, self.course_2.id
        )
        self.assertEqual(response.data[1]["course__title"], self.course_2.title)
        self.assertEqual(response.data[1]["total_challenges"], 1)

    def test_get_challenge_scores_success(self):
        url = reverse("challenge-scores", args=[self.course_1.id])
        self.client.login(username="user_t1", password="pwd1")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data,
            [
                {
                    "challenge_name": self.challenge_1.name,
                    "score": "9.00",
                    "challenge_estimated_time": self.challenge_2.estimated_minutes,
                },
            ],
        )

    def test_get_challenge_scores_no_stats(self):
        url = f"/api/challenge-scores/{self.course_2.id}/"
        self.client.login(username="user_t1", password="pwd1")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_valid_skipped_true(self):
        url = "/api/register-event/"
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "skipped": True,
            "timeout": False,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "ChallengeStat updated successfully."
        )
        self.assertTrue(
            ChallengeStat.objects.filter(
                challenge=self.challenge_1,
                student=self.student_1,
                skipped=True,
                timeout=False,
            ).exists()
        )

    def test_post_valid_timeout_true(self):
        url = "/api/register-event/"
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "skipped": False,
            "timeout": True,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "ChallengeStat updated successfully."
        )
        self.assertTrue(
            ChallengeStat.objects.filter(
                challenge=self.challenge_1,
                student=self.student_1,
                skipped=False,
                timeout=True,
            ).exists()
        )

    def test_post_invalid_both_false(self):
        url = "/api/register-event/"
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": self.challenge_1.id,
            "skipped": False,
            "timeout": False,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Either skipped or timeout must be True and the other False.",
            response.data["non_field_errors"],
        )

    def test_post_invalid_challenge_id(self):
        url = "/api/register-event/"
        self.client.login(username="user_t1", password="pwd1")
        data = {
            "challenge_id": 999,
            "skipped": True,
            "timeout": False,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Challenge with the given ID does not exist.", response.data["challenge_id"]
        )
