import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)


async def run_keep_alive_loop(url: str, interval_seconds: int = 600) -> None:
    """
    Background loop tự động ping URL định kỳ để giữ container luôn thức (cho Free tier)
    """
    if not url:
        logger.info("KEEP_ALIVE_URL is not set. Self-pinger disabled.")
        return

    logger.info("Starting self keep-alive pinger for URL: %s (every %ds)", url, interval_seconds)
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    logger.info("Keep-alive ping to %s returned status %s", url, response.status)
        except asyncio.CancelledError:
            logger.info("Keep-alive loop cancelled.")
            break
        except Exception as e:
            logger.warning("Keep-alive ping to %s failed: %s", url, e)
