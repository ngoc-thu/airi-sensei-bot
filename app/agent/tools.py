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
    Lọc bỏ tag HTML, script, style và trích xuất cấu trúc văn bản/bảng sạch sẽ
    """
    # Xóa script, style, head, svg, nav, footer
    cleaned = re.sub(
        r"<(script|style|head|svg|nav|footer)[^>]*>.*?</\1>",
        " ",
        raw_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Giữ cấu trúc hàng và khối nội dung
    cleaned = re.sub(r"</(tr|p|div|h1|h2|h3|h4|li)>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</td>\s*<td[^>]*>", " | ", cleaned, flags=re.IGNORECASE)
    # Loại bỏ thuộc tính có ngoặc kép để tránh ký tự > trong CSS class (Tailwind/Next.js)
    cleaned = re.sub(r'=\s*"[^"]*"', "", cleaned)
    cleaned = re.sub(r"=\s*'[^']*'", "", cleaned)
    # Xóa toàn bộ HTML tags còn lại
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    text = html.unescape(cleaned)
    # Chuẩn hóa khoảng trắng và dòng
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _search_ddg_sync(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Tìm kiếm qua DuckDuckGo HTML Engine, trích xuất chính xác URL đích và đoạn trích.
    """
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    req = urllib.request.Request(url, headers=headers)
    results: List[Dict[str, str]] = []
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            content = resp.read().decode("utf-8", errors="ignore")

        pattern = (
            r"<a[^>]*class=\"result__a\"[^>]*href=\"([^\"]+)\">(.*?)</a>"
            r".*?<a[^>]*class=\"result__snippet\"[^>]*>(.*?)</a>"
        )
        for match in re.finditer(pattern, content, re.DOTALL):
            raw_url, title_raw, snippet_raw = match.groups()
            if "uddg=" in raw_url:
                actual_url = urllib.parse.unquote(raw_url.split("uddg=")[1].split("&")[0])
            else:
                actual_url = raw_url

            title = html.unescape(re.sub(r"<[^>]+>", "", title_raw)).strip()
            snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_raw)).strip()
            if title and actual_url and not actual_url.startswith("/"):
                results.append({"title": title, "url": actual_url, "snippet": snippet})
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.debug("DuckDuckGo sync search failed: %s", e)
    return results


async def _search_ddg(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    import asyncio
    return await asyncio.to_thread(_search_ddg_sync, query, max_results)


async def _search_bing(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    timeout = aiohttp.ClientTimeout(total=8)
    results: List[Dict[str, str]] = []
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()

        items = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', text, re.DOTALL)
        for item in items:
            title_m = re.search(r'<h2><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', item, re.DOTALL)
            p_m = re.search(r'<p[^>]*>(.*?)</p>', item, re.DOTALL)
            if title_m:
                raw_url = title_m.group(1)
                title = html.unescape(re.sub(r'<[^>]+>', '', title_m.group(2)).strip())
                snippet = html.unescape(re.sub(r'<[^>]+>', '', p_m.group(1)).strip()) if p_m else ""
                if title and raw_url and not raw_url.startswith("/"):
                    results.append({"title": title, "url": raw_url, "snippet": snippet})
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.debug("Bing search failed: %s", e)
    return results


async def web_search(query: str, max_results: int = 4) -> str:
    """
    Tìm kiếm thông tin thời gian thực trên web bằng DuckDuckGo và Bing,
    trả về danh sách tiêu đề, đường dẫn URL chi tiết và đoạn trích.
    """
    try:
        items = await _search_ddg(query, max_results=max_results)
        if not items:
            items = await _search_bing(query, max_results=max_results)

        if items:
            formatted = []
            for i, it in enumerate(items, 1):
                formatted.append(f"{i}. [{it['title']}]({it['url']})\n   {it['snippet']}")
            return "\n\n".join(formatted)

        return f"Không tìm thấy kết quả phù hợp cho: '{query}'."
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
                "Tìm kiếm thông tin thực tế, tin tức mới nhất, tỷ giá, giá vàng, "
                "giá xăng dầu, thời tiết, sự kiện hiện tại trên internet. "
                "Trả về danh sách tiêu đề, đường dẫn URL và đoạn trích. "
                "Nếu cần đọc số liệu chi tiết hoặc toàn bộ bảng giá, hãy lấy URL và gọi tiếp read_webpage(url)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Từ khóa tìm kiếm (ví dụ: 'giá xăng hôm nay Petrolimex', 'giá vàng SJC hôm nay')"
                        ),
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
            "description": (
                "Đọc và trích xuất nội dung chi tiết (bảng giá, số liệu, bảng biểu, bài báo) "
                "từ một đường link URL (do người dùng cung cấp hoặc từ kết quả tìm kiếm web_search)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Địa chỉ URL đầy đủ của trang web (ví dụ: 'https://giaxanghomnay.com/')",
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
    {
        "type": "function",
        "function": {
            "name": "remember_user_fact",
            "description": (
                "Ghi nhớ thông tin cá nhân, tên gọi, biệt danh, sở thích hoặc cách xưng hô "
                "mong muốn của người dùng vào bộ nhớ vĩnh viễn (Persistent Long-Term Memory)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Tên thông tin (ví dụ: 'tên_gọi', 'cách_xưng_hô', 'sở_thích')",
                    },
                    "value": {
                        "type": "string",
                        "description": "Giá trị cần ghi nhớ (ví dụ: 'anh yêu', 'Tiến', 'thích uống cà phê')",
                    },
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_notes",
            "description": (
                "Quản lý sổ tay ghi chú cá nhân (Notes) của người dùng: lưu ghi chú mới, "
                "xem danh sách ghi chú hoặc xóa ghi chú theo mã số."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["save", "list", "delete"],
                        "description": "Thao tác cần thực hiện ('save', 'list', 'delete')",
                    },
                    "title": {
                        "type": "string",
                        "description": "Tiêu đề ghi chú (khi lưu)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Nội dung ghi chú chi tiết",
                    },
                    "note_id": {
                        "type": "integer",
                        "description": "Mã số ID của ghi chú cần xóa (khi delete)",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Đặt lịch hẹn giờ nhắc nhở người dùng trên Telegram sau một số phút cụ thể.",
            "parameters": {
                "type": "object",
                "properties": {
                    "minutes_from_now": {
                        "type": "integer",
                        "description": "Số phút tính từ hiện tại (ví dụ: 15 để nhắc sau 15 phút, 60 là 1 tiếng)",
                    },
                    "message": {
                        "type": "string",
                        "description": "Nội dung cần nhắc nhở",
                    },
                },
                "required": ["minutes_from_now", "message"],
            },
        },
    },
]
