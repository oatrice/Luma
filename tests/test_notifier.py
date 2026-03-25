"""
Tests for luma_core.notifier — Telegram notification via Akasa Backend
TDD: 🟥 RED Phase
"""
from unittest.mock import patch, MagicMock


class TestNotifyTaskComplete:
    """ทดสอบ notify_task_complete function"""

    @patch("luma_core.notifier.requests.post")
    def test_notify_sends_correct_payload(self, mock_post):
        """ส่ง POST ไปยัง Akasa Backend ด้วย payload ที่ถูกต้อง"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"delivered": True}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from luma_core.notifier import notify_task_complete

        with patch("luma_core.notifier.AKASA_CHAT_ID", "12345"), \
             patch("luma_core.notifier.AKASA_API_URL", "http://localhost:8000"), \
             patch("luma_core.notifier.AKASA_API_KEY", "test-key"):
            result = notify_task_complete(
                project="TestProject",
                task="Code Review",
                status="success",
                duration="30s",
            )

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        assert payload["project"] == "TestProject"
        assert payload["task"] == "Code Review"
        assert payload["status"] == "success"
        assert payload["duration"] == "30s"
        assert payload["chat_id"] == "12345"
        assert payload["source"].startswith("Luma CLI (")

    @patch("luma_core.notifier.requests.post")
    def test_notify_skips_when_no_chat_id(self, mock_post):
        """ถ้า AKASA_CHAT_ID ว่าง ต้อง skip ไม่ crash และไม่เรียก API"""
        from luma_core.notifier import notify_task_complete

        with patch("luma_core.notifier.AKASA_CHAT_ID", ""):
            result = notify_task_complete(
                project="TestProject",
                task="Code Review",
                status="success",
            )

        assert result is False
        mock_post.assert_not_called()

    @patch("luma_core.notifier.requests.post")
    def test_notify_handles_network_error(self, mock_post):
        """ถ้า API ล้มเหลว ต้อง catch ไม่ crash Luma"""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        from luma_core.notifier import notify_task_complete

        with patch("luma_core.notifier.AKASA_CHAT_ID", "12345"), \
             patch("luma_core.notifier.AKASA_API_URL", "http://localhost:8000"), \
             patch("luma_core.notifier.AKASA_API_KEY", "test-key"):
            result = notify_task_complete(
                project="TestProject",
                task="Code Review",
                status="failure",
                message="Something went wrong",
            )

        assert result is False

    @patch("luma_core.notifier.requests.post")
    def test_notify_excludes_none_optional_fields(self, mock_post):
        """optional fields ที่เป็น None ต้องไม่ส่งไปใน payload"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"delivered": True}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        from luma_core.notifier import notify_task_complete

        with patch("luma_core.notifier.AKASA_CHAT_ID", "12345"), \
             patch("luma_core.notifier.AKASA_API_URL", "http://localhost:8000"), \
             patch("luma_core.notifier.AKASA_API_KEY", "test-key"):
            notify_task_complete(
                project="TestProject",
                task="Generate Spec",
                status="success",
            )

        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")

        assert "duration" not in payload
        assert "message" not in payload
        assert "link" not in payload

    @patch("luma_core.notifier.requests.post")
    def test_notify_handles_http_error(self, mock_post):
        """ถ้า server ตอบ 500 ต้องไม่ crash"""
        import requests

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        from luma_core.notifier import notify_task_complete

        with patch("luma_core.notifier.AKASA_CHAT_ID", "12345"), \
             patch("luma_core.notifier.AKASA_API_URL", "http://localhost:8000"), \
             patch("luma_core.notifier.AKASA_API_KEY", "test-key"):
            result = notify_task_complete(
                project="TestProject",
                task="Create PR",
                status="success",
            )

        assert result is False
