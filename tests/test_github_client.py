from types import SimpleNamespace

import luma_core.github_client as github_client


class DummyResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


def test_get_github_headers_falls_back_to_gh_auth_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(github_client.config, "GITHUB_TOKEN", None)
    monkeypatch.setattr(
        github_client.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="gh-cli-token\n",
            stderr="",
        ),
    )

    headers = github_client.get_github_headers()

    assert headers == {
        "Authorization": "Bearer gh-cli-token",
        "Accept": "application/vnd.github.v3+json",
    }


def test_create_pull_request_retries_with_gh_cli_token_after_401(
    monkeypatch, capsys
):
    monkeypatch.setenv("GITHUB_TOKEN", "bad-token")
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(github_client.config, "GITHUB_TOKEN", "bad-token")
    monkeypatch.setattr(
        github_client.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="good-gh-token\n",
            stderr="",
        ),
    )

    seen_auth_headers = []
    responses = [
        DummyResponse(401, text='{"message":"Requires authentication"}'),
        DummyResponse(
            201,
            json_data={"html_url": "https://github.com/oatrice/Luma/pull/35"},
        ),
    ]

    def fake_post(url, headers=None, json=None, timeout=10):
        seen_auth_headers.append(headers.get("Authorization"))
        return responses.pop(0)

    monkeypatch.setattr(github_client.requests, "post", fake_post)

    pr_url = github_client.create_pull_request(
        "oatrice/Luma",
        "Test PR",
        "Body",
        "feat/test-branch",
    )

    captured = capsys.readouterr()

    assert pr_url == "https://github.com/oatrice/Luma/pull/35"
    assert seen_auth_headers == [
        "Bearer bad-token",
        "Bearer good-gh-token",
    ]
    assert "Retrying with gh CLI token" in captured.out
