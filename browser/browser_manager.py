import os
import asyncio
from playwright.async_api import async_playwright
from utils.logger import logger
from utils.config import SCREENSHOT_DIR

class BrowserManager:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def launch(self):
        logger.info("Launching Playwright browser context...")
        self.playwright = await async_playwright().start()
        
        # Configure launch options
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-features=RendererCodeIntegrity",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Create standard context (emulating viewport size, user agent, etc.) and ignore SSL warnings
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        # Bypass simple bot detection by removing webdriver property
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Optimize page loading: abort font requests to prevent hang times on slow servers
        async def block_fonts(route):
            url = route.request.url.lower()
            if any(ext in url for ext in [".woff", ".woff2", ".ttf", ".otf", ".eot"]) or "fonts.googleapis" in url or "fonts.gstatic" in url:
                await route.abort()
            else:
                await route.continue_()
        await self.page.route("**/*", block_fonts)
        
        logger.info("Browser window launched successfully.")
        return self.page

    async def get_page(self):
        if not self.page:
            await self.launch()
        return self.page

    async def take_screenshot(self, task_id, step_name):
        if not self.page:
            logger.warning("No active page to take screenshot of.")
            return None
        
        filename = f"task_{task_id}_{step_name}_{int(asyncio.get_event_loop().time())}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        try:
            await self.page.screenshot(path=filepath, full_page=False)
            logger.info(f"Screenshot captured and stored at: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to capture page screenshot: {e}")
            return None

    async def shutdown(self):
        logger.info("Shutting down Playwright browser session...")
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser session terminated.")
        except Exception as e:
            logger.error(f"Error during browser teardown: {e}")
