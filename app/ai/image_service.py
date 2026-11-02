import logging
import urllib.parse
from typing import Tuple
import aiohttp
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


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
        Sinh ảnh với cơ chế fallback tự động (Flux -> Turbo).
        Trả về (bytes_ảnh, model_đã_dùng).
        """
        models = [self.settings.IMAGE_MODEL, self.settings.IMAGE_FALLBACK_MODEL]

        for model in models:
            url = self.build_url(prompt, model=model)
            try:
                logger.info("Generating image with model: %s, prompt: %s", model, prompt[:50])
                image_bytes = await self._fetch_image_bytes(url)
                logger.info("Successfully generated image with model: %s (%d bytes)", model, len(image_bytes))
                return image_bytes, model
            except Exception as e:
                logger.warning("Image generation with model %s failed: %s. Trying fallback...", model, e)

        raise RuntimeError("Tất cả các engine sinh ảnh đều đang bận, vui lòng thử lại sau giây lát!")
