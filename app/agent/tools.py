import ast
import datetime
import html
import logging
import math
import re
import urllib.parse
from typing import Any, Dict, List
import aiohttp

logger = logging.getLogger(__name__)


def get_vietnam_time() -> str:
    """
    Trả về thời gian hiện tại theo múi giờ Việt Nam (GMT+7)
    """
    tz = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz)
    weekday_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][now.weekday()]
    return f"{weekday_vn}, {now.strftime('%d/%m/%Y %H:%M:%S')} - Giờ Việt Nam (GMT+7)"


def safe_calculate(expression: str) -> str:
    """
    Tính toán biểu thức toán học an toàn, chặn mọi hàm nguy hiểm.
    """
    allowed_names = {
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "pi": math.pi,
        "e": math.e,
        "abs": abs,
        "round": round,
    }

    try:
        # Parse AST để kiểm tra an toàn
        node = ast.parse(expression.strip(), mode="eval")
        for subnode in ast.walk(node):
            if isinstance(subnode, (ast.Import, ast.ImportFrom, ast.Call)):
                if isinstance(subnode, ast.Call):
                    if not (isinstance(subnode.func, ast.Name) and subnode.func.id in allowed_names):
                        return "Lỗi: Biểu thức chứa hàm không được phép."
            elif isinstance(subnode, (ast.Attribute, ast.Lambda)):
                return "Lỗi: Không được phép truy cập thuộc tính hoặc lambda."

        compiled = compile(node, "<calc>", "eval")
        result = eval(compiled, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Lỗi tính toán: {e}"


def clean_html_to_text(raw_html: str) -> str:
    """
    Lọc bỏ tag HTML, script, style và trả về văn bản sạch
    """
    # Xóa script và style
    cleaned = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Xóa toàn bộ tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    # Decode entities
    text = html.unescape(cleaned)
    # Chuẩn hóa khoảng trắng
    text = re.sub(r"\s+", " ", text).strip()
    return text


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def web_search(query: str, max_results: int = 4) -> str:
    """
    Tìm kiếm thông tin thời gian thực trên web bằng DuckDuckGo
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return f"Không thể tìm kiếm web (HTTP {resp.status})."
                raw_html = await resp.read()
                content = raw_html.decode("utf-8", errors="ignore")

        snippets = re.findall(r"<a class=\"result__snippet\"[^>]*>(.*?)</a>", content, re.DOTALL)
        titles = re.findall(r"<a class=\"result__url\"[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", content, re.DOTALL)

        if not snippets:
            return "Không tìm thấy kết quả tìm kiếm nào phù hợp."

        results = []
        for i, snippet in enumerate(snippets[:max_results]):
            clean_s = html.unescape(re.sub(r"<[^>]+>", "", snippet).strip())
            results.append(f"{i+1}. {clean_s}")

        return "\n\n".join(results)
    except Exception as e:
        logger.warning("Web search failed for query '%s': %s", query, e)
        return f"Lỗi khi tìm kiếm: {e}"


async def read_webpage(url: str, max_chars: int = 2500) -> str:
    """
    Đọc và trích xuất nội dung văn bản từ một đường link trang web bất kỳ
    """
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        timeout = aiohttp.ClientTimeout(total=12)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return f"Không thể truy cập trang web (HTTP {resp.status})."
                raw_html = await resp.read()
                content = raw_html.decode("utf-8", errors="ignore")

        text = clean_html_to_text(content)
        if len(text) > max_chars:
            text = text[:max_chars] + "...\n[Nội dung đã được rút gọn]"
        return text if text else "Trang web không có nội dung văn bản đọc được."
    except Exception as e:
        logger.warning("Failed to read webpage '%s': %s", url, e)
        return f"Lỗi đọc trang web: {e}"


# Định nghĩa danh sách Tool Schema chuẩn cho LLM Function Calling
AGENT_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Tìm kiếm thông tin thực tế, tin tức mới nhất, tỷ giá, "
                "thời tiết, sự kiện hiện tại trên internet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Từ khóa tìm kiếm (ví dụ: 'giá vàng hôm nay', 'thời tiết Hà Nội')",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Đọc và trích xuất nội dung bài viết từ một đường link URL mà người dùng gửi.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Địa chỉ URL đầy đủ của trang web (ví dụ: 'https://vnexpress.net/...')",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Tạo tranh vẽ nghệ thuật, ảnh minh họa bằng AI từ mô tả chi tiết.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Mô tả bức tranh muốn vẽ (ví dụ: 'một chú mèo phi hành gia 4k')",
                    }
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Thực hiện phép tính toán học, biểu thức tài chính, chuyển đổi số học chính xác 100%.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Biểu thức toán học (ví dụ: '(120 * 45) + 350', 'sqrt(144) * 5', '2**16')",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Lấy ngày tháng, thứ trong tuần và giờ hiện tại chính xác của Việt Nam (GMT+7).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]
