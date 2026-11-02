import pytest
from aiohttp.test_utils import TestClient, TestServer
from app.config import Settings
from app.server.web import create_web_app


@pytest.mark.asyncio
async def test_health_endpoint():
    settings = Settings(BOT_TOKEN="test_token", PORT=8080)
    app = create_web_app(settings=settings)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        response = await client.get("/health")
        assert response.status == 200
        data = await response.json()
        assert data["status"] == "ok"
        assert data["service"] == "AiriSenseiBot"
        assert "uptime_seconds" in data
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_root_endpoint():
    settings = Settings(BOT_TOKEN="test_token", PORT=8080)
    app = create_web_app(settings=settings)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()

    try:
        response = await client.get("/")
        assert response.status == 200
        text = await response.text()
        assert "Airi Sensei" in text
    finally:
        await client.close()
