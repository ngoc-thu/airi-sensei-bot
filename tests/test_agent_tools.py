import pytest
from app.agent.tools import safe_calculate, get_vietnam_time, clean_html_to_text


def test_safe_calculate():
    assert safe_calculate("2 + 2 * 3") == "8"
    assert safe_calculate("(10 - 4) / 2") == "3.0"
    assert safe_calculate("2 ** 10") == "1024"
    assert "Lỗi" in safe_calculate("__import__('os')")


def test_get_vietnam_time():
    vtime = get_vietnam_time()
    assert "Giờ Việt Nam (GMT+7)" in vtime


def test_clean_html_to_text():
    html = "<html><head><style>body{}</style></head><body><h1>Tiêu đề</h1><p>Nội dung bài viết.</p></body></html>"
    text = clean_html_to_text(html)
    assert "Tiêu đề" in text
    assert "Nội dung bài viết." in text
    assert "style" not in text


def test_clean_html_to_text_tables():
    raw = (
        '<table><tr class="[&>td]:p-2"><td>Xăng RON 95</td><td>24,000</td></tr>'
        "<tr><td>Xăng E5</td><td>23,500</td></tr></table>"
    )
    text = clean_html_to_text(raw)
    assert "Xăng RON 95 | 24,000" in text
    assert "Xăng E5 | 23,500" in text
