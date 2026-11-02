import asyncio
import logging
import re
import urllib.parse
from typing import Tuple
import aiohttp
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def clean_prompt(prompt: str) -> str:
    """
    Loại bỏ các từ khóa thừa tiếng Việt như:
    'tạo ảnh', 'vẽ ảnh', 'vẽ tranh', 'bức ảnh', 'hình ảnh', etc.
    """
    cleaned = prompt.strip()
    patterns = [
        r"^(?:hãy\s+)?(?:tạo|vẽ|sinh|generate|draw)\s+(?:cho\s+(?:mình|em|anh|tôi)\s+)?(?:bức\s+)?(?:ảnh|tranh|hình|image|picture)?\s*(?:về|với)?\s*",
        r"^(?:tạo\s+ảnh|vẽ\s+ảnh|vẽ\s+tranh|vẽ\s+hình)\s*[:\s]*",
        r"^(?:bức\s+ảnh|bức\s+tranh|hình\s+ảnh)\s+(?:về|của)?\s*",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else prompt.strip()


async def translate_prompt(prompt: str) -> str:
    """
    Dịch và tối ưu hóa prompt tiếng Việt sang tiếng Anh chuyên sâu cho Flux / SDXL.
    Ví dụ: 'con mèo' -> 'A cute fluffy cat, realistic portrait, highly detailed'.
    """
    cleaned = clean_prompt(prompt)

    # Nếu prompt đã hoàn toàn là tiếng Anh dài hơn 2 từ thì dùng luôn
    if all(ord(c) < 128 for c in cleaned) and len(cleaned.split()) > 2:
        return cleaned

    try:
        url = "https://text.pollinations.ai/"
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert prompt engineer for Flux and Stable Diffusion image generators. "
                        "Translate the user's Vietnamese prompt into a concise, vivid English prompt. "
                        "Output ONLY the English prompt with no quotation marks, no explanation, no extra words."
                    )
                },
                {"role": "user", "content": cleaned}
            ]
        }
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    result = (await resp.text()).strip().strip('"\'')
                    if result and len(result) > 3:
                        logger.info("Enhanced image prompt: '%s' -> '%s'", cleaned, result)
                        return result
    except Exception as e:
        logger.warning("Prompt translation failed or timed out: %s. Using cleaned prompt.", e)

    return cleaned


class ImageService:
    BASE_URL = "https://image.pollinations.ai/prompt"

    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()

    def build_url(self, prompt: str, model: str = "flux", width: int = 1024, height: int = 1024) -> str:
        """
        Tạo URL sinh ảnh trực tiếp từ Pollinations AI
        """
        encoded_prompt = urllib.parse.quote(prompt.strip())
        query = urllib.parse.urlencode({
            "model": model,
            "width": width,
            "height": height,
            "nologo": "true",
            "enhance": "true",
        })
        return f"{self.BASE_URL}/{encoded_prompt}?{query}"

    async def _fetch_image_bytes(self, url: str) -> bytes:
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Image generation failed with HTTP status {response.status}")
                return await response.read()

    async def generate_image(self, prompt: str) -> Tuple[bytes, str]:
        """
        Sinh ảnh với cơ chế tự động dịch sang tiếng Anh và fallback (Flux -> Turbo).
        Trả về (bytes_ảnh, model_đã_dùng).
        """
        # Tự động làm sạch và dịch sang tiếng Anh chuyên sâu cho Flux
        english_prompt = await translate_prompt(prompt)

        models = [self.settings.IMAGE_MODEL, self.settings.IMAGE_FALLBACK_MODEL]

        for model in models:
            url = self.build_url(english_prompt, model=model)
            try:
                logger.info("Generating image with model: %s, prompt: %s", model, english_prompt[:60])
                image_bytes = await self._fetch_image_bytes(url)
                logger.info("Successfully generated image with model: %s (%d bytes)", model, len(image_bytes))
                return image_bytes, model
            except Exception as e:
                logger.warning("Image generation with model %s failed: %s. Trying fallback...", model, e)

        raise RuntimeError("Tất cả các engine sinh ảnh đều đang bận, vui lòng thử lại sau giây lát!")
