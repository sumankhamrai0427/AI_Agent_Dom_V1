from utils.logger import logger

class DOMReader:
    @staticmethod
    async def extract_interactive_elements(page):
        """Executes a JS script on the page to return visible interactive nodes."""
        if not page:
            return []
            
        js_script = """
        () => {
            const elements = [];
            const interactiveSelectors = 'button, input, select, textarea, a, [role="button"], [role="checkbox"]';
            const nodes = document.querySelectorAll(interactiveSelectors);
            
            nodes.forEach((node, idx) => {
                // Only capture visible elements
                const rect = node.getBoundingClientRect();
                const style = window.getComputedStyle(node);
                if (rect.width === 0 || rect.height === 0 || style.display === 'none' || style.visibility === 'hidden') {
                    return;
                }
                
                // Get selector info
                let selector = node.tagName.toLowerCase();
                if (node.id) {
                    selector += '#' + node.id;
                } else if (node.className) {
                    selector += '.' + Array.from(node.classList).join('.');
                }
                
                // Determine text label
                let text = node.innerText || node.value || node.getAttribute('placeholder') || '';
                text = text.trim().substring(0, 50);
                
                // For select dropdowns, fetch options
                let options = [];
                if (node.tagName.toLowerCase() === 'select') {
                    options = Array.from(node.options).map(opt => ({
                        text: opt.text.trim(),
                        value: opt.value
                    }));
                }
                
                elements.push({
                    index: idx,
                    tagName: node.tagName.toLowerCase(),
                    id: node.id || null,
                    type: node.type || null,
                    name: node.name || null,
                    placeholder: node.getAttribute('placeholder') || null,
                    text: text,
                    selector: selector,
                    options: options,
                    rect: {
                        x: Math.round(rect.left),
                        y: Math.round(rect.top),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height)
                    }
                });
            });
            return elements;
        }
        """
        try:
            elements = await page.evaluate(js_script)
            return elements
        except Exception as e:
            logger.error(f"Failed to evaluate DOM elements: {e}")
            return []

    @classmethod
    async def get_dom_summary(cls, page):
        """Returns a string-formatted summary of interactive page elements for the LLM context."""
        elements = await cls.extract_interactive_elements(page)
        if not elements:
            return "No visible interactive elements found on the current page."
            
        lines = []
        for el in elements:
            el_type = el['tagName']
            if el['type']:
                el_type += f"[{el['type']}]"
                
            selector_desc = f"Selector: `{el['selector']}`"
            if el['id']:
                selector_desc = f"ID: `{el['id']}`"
                
            label = el['text'] or el['placeholder'] or ""
            label_desc = f"Label/Text: '{label}'" if label else ""
            
            option_desc = ""
            if el['options']:
                opt_texts = [f"'{o['text']}'" for o in el['options'][:5]]
                option_desc = f"Options: [{', '.join(opt_texts)}...]"
                
            lines.append(f"- [{el['index']}] <{el_type}> {label_desc} | {selector_desc} {option_desc}".strip())
            
        return "\n".join(lines)
