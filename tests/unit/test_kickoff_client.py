"""Unit tests for mycrew.kickoff_client."""

from unittest.mock import MagicMock, patch

import pytest
import httpx

from mycrew.kickoff_client import KickoffClient, main


class TestKickoffClientInit:
    """Tests for KickoffClient initialization."""

    def test_default_values(self):
        """Default base_url is localhost:8000 and timeout is 30."""
        client = KickoffClient()
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30

    def test_custom_values(self):
        """Custom base_url and timeout are set correctly."""
        client = KickoffClient(base_url="http://custom:9000", timeout=60)
        assert client.base_url == "http://custom:9000"
        assert client.timeout == 60


class TestKickoffClientRun:
    """Tests for KickoffClient.run() method."""

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_success(self, mock_post):
        """Successful POST returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "accepted",
            "issue_url": "https://github.com/owner/repo/issues/1",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = KickoffClient()
        result = client.run(
            issue_url="https://github.com/owner/repo/issues/1",
            branch="main",
            from_scratch=False,
            max_retries=3,
            dry_run=False,
            programmatic=False,
        )

        assert result == {
            "status": "accepted",
            "issue_url": "https://github.com/owner/repo/issues/1",
        }
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert (
            call_kwargs["json"]["issue_url"] == "https://github.com/owner/repo/issues/1"
        )
        assert call_kwargs["json"]["branch"] == "main"
        assert call_kwargs["json"]["from_scratch"] is False
        assert call_kwargs["json"]["max_retries"] == 3
        assert call_kwargs["json"]["dry_run"] is False
        assert call_kwargs["json"]["programmatic"] is False
        assert call_kwargs["timeout"] == 30

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_with_all_options(self, mock_post):
        """All parameters are passed in payload."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "queued"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = KickoffClient()
        result = client.run(
            issue_url="https://github.com/owner/repo/issues/42",
            branch="develop",
            from_scratch=True,
            max_retries=5,
            dry_run=True,
            programmatic=True,
        )

        payload = mock_post.call_args[1]["json"]
        assert payload["issue_url"] == "https://github.com/owner/repo/issues/42"
        assert payload["branch"] == "develop"
        assert payload["from_scratch"] is True
        assert payload["max_retries"] == 5
        assert payload["dry_run"] is True
        assert payload["programmatic"] is True

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_raises_on_http_error(self, mock_post):
        """HTTP 4xx/5xx raises HTTPStatusError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        client = KickoffClient()
        with pytest.raises(httpx.HTTPStatusError):
            client.run(issue_url="https://github.com/owner/repo/issues/1")

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_raises_on_connection_error(self, mock_post):
        """Connection error raises ConnectError."""
        mock_post.side_effect = httpx.ConnectError("Connection failed")

        client = KickoffClient()
        with pytest.raises(httpx.ConnectError):
            client.run(issue_url="https://github.com/owner/repo/issues/1")

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_raises_on_timeout(self, mock_post):
        """Timeout raises TimeoutException."""
        mock_post.side_effect = httpx.TimeoutException("Timed out")

        client = KickoffClient()
        with pytest.raises(httpx.TimeoutException):
            client.run(issue_url="https://github.com/owner/repo/issues/1")

    @patch("mycrew.kickoff_client.httpx.post")
    def test_run_custom_timeout(self, mock_post):
        """Custom timeout is passed to httpx.post."""
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = KickoffClient(timeout=120)
        client.run(issue_url="https://github.com/owner/repo/issues/1")

        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["timeout"] == 120


class TestKickoffClientCLI:
    """Tests for CLI argument parsing."""

    def test_cli_issue_url_required(self):
        """Positional argument issue_url is required."""
        with patch("mycrew.kickoff_client.KickoffClient.run") as mock_run:
            mock_run.return_value = {}
            with pytest.raises(SystemExit):
                main()

    @patch("mycrew.kickoff_client.KickoffClient.run")
    def test_cli_parse_minimal(self, mock_run):
        """Minimal args: issue_url only."""
        mock_run.return_value = {}
        with patch(
            "sys.argv", ["kickoff-client", "https://github.com/owner/repo/issues/1"]
        ):
            main()
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["issue_url"] == "https://github.com/owner/repo/issues/1"
        assert call_kwargs["branch"] == "main"
        assert call_kwargs["from_scratch"] is False
        assert call_kwargs["max_retries"] == 3
        assert call_kwargs["dry_run"] is False
        assert call_kwargs["programmatic"] is False

    @patch("mycrew.kickoff_client.KickoffClient.run")
    def test_cli_parse_all_options(self, mock_run):
        """All CLI options are parsed correctly."""
        mock_run.return_value = {}
        with patch(
            "sys.argv",
            [
                "kickoff-client",
                "https://github.com/owner/repo/issues/1",
                "--branch",
                "develop",
                "--from-scratch",
                "--max-retries",
                "5",
                "--dry-run",
                "--programmatic",
                "--url",
                "http://custom:9000",
            ],
        ):
            main()
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["issue_url"] == "https://github.com/owner/repo/issues/1"
        assert call_kwargs["branch"] == "develop"
        assert call_kwargs["from_scratch"] is True
        assert call_kwargs["max_retries"] == 5
        assert call_kwargs["dry_run"] is True
        assert call_kwargs["programmatic"] is True

    @patch("mycrew.kickoff_client.print")
    @patch("mycrew.kickoff_client.KickoffClient.run")
    def test_cli_prints_result(self, mock_run, mock_print):
        """CLI prints the result of run()."""
        mock_run.return_value = {"status": "accepted", "issue_url": "https://x"}
        with patch(
            "sys.argv", ["kickoff-client", "https://github.com/owner/repo/issues/1"]
        ):
            main()
        mock_print.assert_called_once_with(
            {"status": "accepted", "issue_url": "https://x"}
        )
