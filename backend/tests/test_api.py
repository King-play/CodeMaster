from app.main import app
from fastapi.testclient import TestClient


def login(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    response = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_review_task_demo_flow() -> None:
    with TestClient(app) as client:
        token = login(client)
        response = client.post(
            "/api/review-tasks",
            headers=auth_header(token),
            json={
                "project_name": "Test Project",
                "file_name": "sample.py",
                "language": "python",
                "source_kind": "snippet",
                "code": "def price(amount):\n    if amount < 0:\n        return 0\n    return amount\n",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["issues"]
    assert data["test_cases"]


def test_report_exports() -> None:
    with TestClient(app) as client:
        token = login(client)
        task_response = client.post(
            "/api/review-tasks",
            headers=auth_header(token),
            json={
                "project_name": "Report Project",
                "file_name": "sample.py",
                "language": "python",
                "source_kind": "snippet",
                "code": "def price(amount):\n    return amount\n",
            },
        )
        task_id = task_response.json()["id"]
        for extension, media_type in [
            ("md", "text/markdown; charset=utf-8"),
            ("pdf", "application/pdf"),
            (
                "docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ]:
            response = client.get(
                f"/api/review-tasks/{task_id}/report.{extension}",
                headers=auth_header(token),
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == media_type
            assert response.content


def test_review_task_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/review-tasks",
            json={
                "project_name": "No Auth",
                "file_name": "sample.py",
                "code": "print('hi')",
            },
        )

    assert response.status_code == 401


def test_admin_can_manage_prompt_templates() -> None:
    with TestClient(app) as client:
        token = login(client)
        response = client.post(
            "/api/admin/prompt-templates",
            headers=auth_header(token),
            json={
                "name": "security-review",
                "template": "Focus on authentication, authorization, secret handling, and injection risks.",
                "version": "1.0.0",
                "enabled": True,
            },
        )

    assert response.status_code in {200, 409}


def test_developer_cannot_read_admin_users() -> None:
    with TestClient(app) as client:
        token = login(client, "developer", "developer123")
        response = client.get("/api/admin/users", headers=auth_header(token))

    assert response.status_code == 403
