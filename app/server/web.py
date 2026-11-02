import time
from aiohttp import web
from app.config import Settings, get_settings

SERVER_START_TIME = time.time()


async def health_handler(request: web.Request) -> web.Response:
    uptime_sec = int(time.time() - SERVER_START_TIME)
    return web.json_response({
        "status": "ok",
        "service": "AiriSenseiBot",
        "uptime_seconds": uptime_sec,
        "timestamp": int(time.time()),
    })


async def root_handler(request: web.Request) -> web.Response:
    html = """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <title>Airi Sensei Telegram Bot</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                   text-align: center; padding: 50px; background: #0f172a; color: #f8fafc; }
            h1 { color: #38bdf8; }
            p { font-size: 1.2rem; color: #94a3b8; }
            .badge { display: inline-block; padding: 6px 16px; background: #22c55e;
                     color: white; border-radius: 9999px; font-weight: bold; margin-top: 10px; }
            a { color: #38bdf8; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🌸 Airi Sensei Telegram Bot 🌸</h1>
        <div class="badge">Running 24/7 on Render</div>
        <p>Bot AI thông minh hỗ trợ Hỏi đáp và Tạo ảnh nghệ thuật</p>
        <p>Chat trực tiếp trên Telegram: <a href="https://t.me/AiriSenseiBot" target="_blank">@AiriSenseiBot</a></p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


def create_web_app(settings: Settings = None) -> web.Application:
    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/healthz", health_handler)
    return app
