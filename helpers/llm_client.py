import os
import json
import requests
from utils.config import MISTRAL_API_KEY, GEMINI_API_KEY, MISTRAL_MODEL, GEMINI_MODEL, ACTIVE_LLM, MISTRAL_LOCAL_URL, MISTRAL_LOCAL_MODEL
from utils.logger import logger

class LLMClient:
    @staticmethod
    def _call_gemini(prompt, system_instruction=None, response_schema=None):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        
        contents = {"parts": [{"text": prompt}]}
        payload = {
            "contents": [contents],
            "generationConfig": {
                "temperature": 0.2,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if response_schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"
            # Some platforms require schema. For simplicity, we just pass mimeType="application/json"
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                return text
            else:
                logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
                raise RuntimeError(response.text)
        except Exception as e:
            logger.error(f"Gemini Call failed: {e}")
            raise e

    @staticmethod
    def _call_mistral(prompt, system_instruction=None, response_format_json=False):
        if not MISTRAL_API_KEY:
            raise ValueError("MISTRAL_API_KEY is not set")
            
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": MISTRAL_MODEL,
            "messages": messages,
            "temperature": 0.2
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                text = res_data['choices'][0]['message']['content']
                return text
            else:
                logger.error(f"Mistral API Error: {response.status_code} - {response.text}")
                raise RuntimeError(response.text)
        except Exception as e:
            logger.error(f"Mistral Call failed: {e}")
            raise e

    @staticmethod
    def _call_local_mistral(prompt, system_instruction=None, json_mode=False):
        if not MISTRAL_LOCAL_URL:
            raise ValueError("MISTRAL_LOCAL_URL is not set")
            
        url = f"{MISTRAL_LOCAL_URL}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": MISTRAL_LOCAL_MODEL,
            "messages": messages,
            "temperature": 0.2
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                res_data = response.json()
                text = res_data['choices'][0]['message']['content']
                return text
            else:
                logger.error(f"Local Mistral API Error: {response.status_code} - {response.text}")
                raise RuntimeError(response.text)
        except Exception as e:
            logger.error(f"Local Mistral Call failed: {e}")
            raise e

    @classmethod
    def call_llm(cls, prompt, system_instruction=None, json_mode=False):
        # 1. Try Local Mistral first (if configured/available)
        if MISTRAL_LOCAL_URL:
            try:
                logger.info(f"Calling Local Mistral ({MISTRAL_LOCAL_MODEL})...")
                return cls._call_local_mistral(prompt, system_instruction, json_mode=json_mode)
            except Exception as e:
                logger.warning(f"Local Mistral failed, attempting fallback. Error: {e}")

        # 2. Try Mistral Cloud next if API key is configured
        if MISTRAL_API_KEY:
            try:
                logger.info(f"Calling Mistral Cloud ({MISTRAL_MODEL})...")
                return cls._call_mistral(prompt, system_instruction, response_format_json=json_mode)
            except Exception as e:
                logger.warning(f"Mistral Cloud failed, attempting fallback. Error: {e}")

        # 3. Try Gemini as fallback if API key is configured
        if GEMINI_API_KEY:
            try:
                logger.info(f"Calling Gemini ({GEMINI_MODEL})...")
                return cls._call_gemini(prompt, system_instruction, response_schema=json_mode)
            except Exception as e:
                logger.warning(f"Gemini call failed. Error: {e}")

        # 4. If all failed or no keys configured, fallback to simulation mode
        logger.warning("No API Keys configured or calls failed. Operating in Simulation Mode.")
        return cls._simulate_response(prompt, json_mode)

    @classmethod
    def _simulate_response(cls, prompt, json_mode):
        prompt_lower = prompt.lower()
        if "break down" in prompt_lower or "workflow task list" in prompt_lower or "execution plan" in prompt_lower or "planner" in prompt_lower:
            plan = [
                {"id": 1, "task": "Extract Document Data", "status": "PENDING"},
                {"id": 2, "task": "Validate Extracted Data", "status": "PENDING"},
                {"id": 3, "task": "Search Government Portal", "status": "PENDING"},
                {"id": 4, "task": "Extract Land Records", "status": "PENDING"},
                {"id": 5, "task": "Verify Findings", "status": "PENDING"},
                {"id": 6, "task": "Retrieve GIS Coordinates", "status": "PENDING"},
                {"id": 7, "task": "Generate Final Report", "status": "PENDING"}
            ]
            return json.dumps(plan) if json_mode else str(plan)

        elif "document text content" in prompt_lower or "paddleocr" in prompt_lower or "easyocr" in prompt_lower or "analyze the following document" in prompt_lower:
            data = {
                "owner_name": "Ramesh Kumar",
                "father_name": "Suresh Kumar",
                "village": "Bara",
                "district": "Varanasi",
                "khata": "452",
                "khasra": "120",
                "survey_no": "SV-981",
                "area": "1.25 Hectares",
                "reference_number": "REF-UP-2026-902",
                "raw_text": "Extracted text content showing Ramesh Kumar, father Suresh Kumar, village Bara in district Varanasi. Khata 452 and khasra 120."
            }
            return json.dumps(data) if json_mode else str(data)

        elif "observe" in prompt_lower or "browser status" in prompt_lower or "interactive elements" in prompt_lower:
            # Simulated Browser Loop decisions
            # We check execution history or URL to decide what action to yield
            decision = {
                "reasoning": "Determined government portal and current state fields. Form inputs need to be populated step-by-step.",
                "next_action": {
                    "action": "wait",
                    "selector": "",
                    "value": "",
                    "coordinates": None
                },
                "confidence": 0.98,
                "expected_result": "Page elements state updated"
            }
            
            if "select district" in prompt_lower or "district_list" in prompt_lower:
                decision["next_action"] = {"action": "select_dropdown", "selector": "#district_list", "value": "Varanasi"}
            elif "select tehsil" in prompt_lower or "tehsil_list" in prompt_lower:
                decision["next_action"] = {"action": "select_dropdown", "selector": "#tehsil_list", "value": "Pindra"}
            elif "select village" in prompt_lower or "village_list" in prompt_lower:
                decision["next_action"] = {"action": "select_dropdown", "selector": "#village_list", "value": "Bara"}
            elif "enter khata" in prompt_lower or "khata_no" in prompt_lower:
                decision["next_action"] = {"action": "type", "selector": "#khata_no", "value": "452"}
            elif "captcha" in prompt_lower:
                decision["reasoning"] = "CAPTCHA image detected on form. Pausing execution for human solving."
                decision["next_action"] = {"action": "wait", "selector": "#captcha_image", "value": "CAPTCHA"}
            
            return json.dumps(decision) if json_mode else str(decision)

        elif "validate" in prompt_lower or "conflict" in prompt_lower or "compare the following" in prompt_lower:
            is_valid = True
            conflicts = []
            if "dinesh" in prompt_lower:
                is_valid = False
                conflicts.append("Owner Name discrepancy: Deed has 'RAMESH KUMAR', Portal has 'DINESH KUMAR'")
            
            res = {
                "is_valid": is_valid,
                "conflicts": conflicts,
                "normalized_data": {
                    "owner_name": "RAMESH KUMAR" if is_valid else "RAMESH KUMAR / DINESH KUMAR",
                    "father_name": "SURESH KUMAR",
                    "village": "BARA",
                    "district": "VARANASI",
                    "khata": "452",
                    "khasra": "120",
                    "area": "1.25 Hectares"
                }
            }
            return json.dumps(res) if json_mode else str(res)

        return json.dumps({"status": "unknown", "text": prompt[:100]}) if json_mode else prompt[:100]
