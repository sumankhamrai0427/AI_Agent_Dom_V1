from utils.logger import logger

class BrowserUtils:
    @staticmethod
    async def highlight_element(page, selector):
        """Draws a red border around the target element to aid visual tracing."""
        if not page or not selector:
            return
        script = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.style.outline = '3px solid red';
                el.style.outlineOffset = '2px';
            }}
        }}
        """
        try:
            await page.evaluate(script)
        except Exception as e:
            logger.error(f"Failed to highlight element {selector}: {e}")

    @staticmethod
    async def remove_highlight(page, selector):
        """Removes the visual highlight from the element."""
        if not page or not selector:
            return
        script = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.style.outline = '';
                el.style.outlineOffset = '';
            }}
        }}
        """
        try:
            await page.evaluate(script)
        except Exception as e:
            logger.debug(f"Failed to remove highlight from {selector}: {e}")
