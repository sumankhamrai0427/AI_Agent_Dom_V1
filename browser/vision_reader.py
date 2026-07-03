import os
import base64
import json
from utils.logger import logger
from helpers.llm_client import LLMClient

class VisionReader:
    @staticmethod
    def encode_image(image_path):
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    @classmethod
    async def locate_element_by_vision(cls, page, screenshot_path, element_description):
        """Sends screenshot and text description to the LLM to locate click coordinates [x, y]."""
        logger.info(f"Using Vision Reader to locate element: '{element_description}'")
        
        if not screenshot_path or not os.path.exists(screenshot_path):
            logger.warning("No screenshot available for vision localization.")
            return None

        # Base64 encode screenshot
        try:
            base64_image = cls.encode_image(screenshot_path)
        except Exception as e:
            logger.error(f"Failed to encode screenshot: {e}")
            return None

        prompt = f"""
        Analyze the attached screenshot and locate the element described as: '{element_description}'.
        Return the approximate [X, Y] pixel coordinates in the browser viewport (which is 1280x800).
        Respond ONLY with a valid JSON block of the format:
        {{
            "element_found": true,
            "coordinates": [x, y],
            "confidence": 0.90,
            "reasoning": "Description of why these coordinates match."
        }}
        """
        
        system_instruction = "You are a specialized browser vision agent. You parse screenshots to find pixel coordinates of elements."
        
        try:
            # We make a LLM call. If API keys exist and support vision, they will respond.
            # In our mock client, we handle coordinate estimation for safety.
            response_text = LLMClient.call_llm(prompt, system_instruction=system_instruction, json_mode=True)
            data = json.loads(response_text)
            
            if data.get("element_found") and data.get("coordinates"):
                logger.info(f"Vision matched element at: {data['coordinates']} with confidence {data.get('confidence')}")
                return data["coordinates"]
        except Exception as e:
            logger.error(f"Vision API call failed: {e}. Attempting DOM fallback coordinates.")
            
        # DOM fallback: Let's query elements on page matching description
        try:
            fallback_js = f"""
            () => {{
                const el = Array.from(document.querySelectorAll('button, input, a, label')).find(node => {{
                    const text = (node.innerText || node.value || '').toLowerCase();
                    return text.includes('{element_description.lower()}');
                }});
                if (el) {{
                    const rect = el.getBoundingClientRect();
                    return [Math.round(rect.left + rect.width / 2), Math.round(rect.top + rect.height / 2)];
                }}
                return null;
            }}
            """
            coords = await page.evaluate(fallback_js)
            if coords:
                logger.info(f"DOM fallback coordinates found: {coords}")
                return coords
        except Exception as ex:
            logger.error(f"DOM coordinate fallback failed: {ex}")

        return None
