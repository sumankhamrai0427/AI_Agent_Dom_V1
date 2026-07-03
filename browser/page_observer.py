import asyncio
from utils.logger import logger

class PageObserver:
    @staticmethod
    async def is_page_loaded(page):
        """Verifies if the page document has loaded fully."""
        try:
            state = await page.evaluate("document.readyState")
            return state == "complete"
        except Exception:
            return False

    @staticmethod
    async def detect_captcha(page):
        """Detects whether a CAPTCHA challenge is currently present on the page."""
        if not page:
            return False
            
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//iframe[contains(@src, 'hcaptcha')]",
            "//iframe[contains(@src, 'turnstile')]",
            "//div[contains(@class, 'g-recaptcha')]",
            "//div[contains(@id, 'captcha')]",
            "//img[contains(@id, 'captcha')]",
            "//img[contains(@src, 'captcha')]",
            "//img[contains(@src, 'Captcha')]",
            "//img[contains(@src, 'ImageServlet')]",
            "//input[contains(@id, 'InputField2')]",
            "//input[contains(@placeholder, 'captcha')]",
            "//input[contains(@placeholder, 'code') and contains(@placeholder, 'security')]"
        ]
        
        for xpath in captcha_indicators:
            try:
                # Check selector visibility
                loc = page.locator(xpath)
                count = await loc.count()
                for i in range(count):
                    element = loc.nth(i)
                    if await element.is_visible():
                        logger.warning(f"CAPTCHA detected via indicator: {xpath}")
                        return True
            except Exception:
                continue

        # Also search text contents for common words
        try:
            text_content = await page.content()
            text_content_lower = text_content.lower()
            captcha_words = ["enter captcha", "security code", "verify code", "are you human", "solve puzzle"]
            for word in captcha_words:
                if word in text_content_lower:
                    logger.warning(f"CAPTCHA detected via text content keyword: '{word}'")
                    return True
        except Exception:
            pass

        return False

    @staticmethod
    async def is_error_page(page):
        """Detects if page has crashed or displays web portal down / gateway errors."""
        if not page:
            return False
            
        error_keywords = [
            "404 not found",
            "502 bad gateway",
            "503 service temporarily unavailable",
            "internal server error",
            "site cannot be reached",
            "connection timed out"
        ]
        try:
            title = (await page.title()).lower()
            text = (await page.inner_text("body")).lower()
            
            for keyword in error_keywords:
                if keyword in title or keyword in text[:300]:
                    logger.error(f"Error page detected with signature: '{keyword}'")
                    return True
        except Exception:
            pass
            
        return False
