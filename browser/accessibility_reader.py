from utils.logger import logger

class AccessibilityReader:
    @staticmethod
    async def get_accessibility_snapshot(page):
        """Uses Playwright's page.accessibility.snapshot() to fetch accessible tree elements."""
        if not page or not hasattr(page, "accessibility"):
            return {}
        try:
            snapshot = await page.accessibility.snapshot()
            return snapshot or {}
        except Exception as e:
            logger.debug(f"Failed to fetch accessibility snapshot: {e}")
            return {}

    @classmethod
    async def get_accessibility_summary(cls, page):
        """Produces a simplified string text mapping roles and accessible names for LLM reasoning."""
        snapshot = await cls.get_accessibility_snapshot(page)
        if not snapshot:
            # Fallback: Parse ARIA attributes directly from DOM
            js_fallback = """
            () => {
                const results = [];
                const ariaElements = document.querySelectorAll('[aria-label], [aria-labelledby], [role]');
                ariaElements.forEach((el, idx) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            role: el.getAttribute('role') || el.tagName.toLowerCase(),
                            name: el.getAttribute('aria-label') || el.innerText || '',
                            id: el.id || ''
                        });
                    }
                });
                return results;
            }
            """
            try:
                aria_items = await page.evaluate(js_fallback)
                if aria_items:
                    lines = [f"- Role: '{item['role']}', Name: '{item['name']}', ID: '{item['id']}'" for item in aria_items[:20]]
                    return "Accessibility Tree (Aria Direct):\n" + "\n".join(lines)
            except Exception:
                pass
            return "No accessibility snapshot or ARIA selectors retrieved."

        # Flatten the accessibility tree into structured lines
        lines = []
        cls._flatten_snapshot(snapshot, lines, indent=0)
        return "\n".join(lines[:30]) # Limit to first 30 entries for tokens efficiency

    @classmethod
    def _flatten_snapshot(cls, node, lines, indent=0):
        if not node:
            return
            
        role = node.get("role", "generic")
        name = node.get("name", "")
        value = node.get("value", "")
        
        desc = ""
        if name:
            desc += f"Name: '{name}'"
        if value:
            desc += f" Value: '{value}'"
            
        if desc:
            lines.append("  " * indent + f"- {role.capitalize()}: {desc}")
            
        children = node.get("children", [])
        for child in children:
            cls._flatten_snapshot(child, lines, indent + 1)
