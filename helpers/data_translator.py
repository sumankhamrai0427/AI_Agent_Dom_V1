# helpers/data_translator.py
from helpers.llm_client import LLMClient
import json

class DataTranslator:
    @staticmethod
    def translate_to_portal_schema(extracted_data, portal_name, portal_options=None):
        """
        extracted_data: {'owner_name': 'Rajesh Kumar Das', 'village': 'Baruipara', ...}
        portal_name: 'Banglarbhumi'
        portal_options: ড্রপডাউন অপশনের তালিকা (যেমন ওয়েবসাইটের সমস্ত জেলা বা ব্লকের তালিকা)
        """
        system_instruction = f"""
        You are a Data Adapter and Translator.
        Your goal is to prepare the extracted document data for entry into the '{portal_name}' portal.
        
        Expected Languages/Scripts of Portals:
        - 'Banglarbhumi' (West Bengal): Expects ENGLISH/LATIN script for search inputs and dropdowns (e.g., "HOOGHLY", "BARUIPARA").
        - 'Bhu Naksha UP' / 'Bihar Bhumi': Expects HINDI/DEVANAGARI or ENGLISH/LATIN script.
        - Other portals: Expect English/Latin by default.
        
        Workflow:
        1. Identify the language/script of the input 'Extracted Document Data' (e.g., Bengali, Hindi, English).
        2. Identify the expected language/script of the target portal '{portal_name}'.
        3. Determine if there is a mismatch.
           - If the input language/script matches the portal's expected language/script, DO NOT translate. Return the fields in their original language/script.
           - If there is a mismatch (e.g., input is in Bengali script but portal expectations are English/Latin), translate/transliterate the text fields (district, village, block, owner_name) to the portal's expected language/script.
        4. Preserve all codes (like district_code, tehsil_code, village_code, khata, khasra) exactly as they are without change.
        
        Return the result as a valid JSON object matching the input keys.
        """
        
        prompt = f"""
        Extracted Document Data:
        {json.dumps(extracted_data)}
        
        Target Portal Options (if any):
        {json.dumps(portal_options) if portal_options else "None"}
        
        Please map and translate:
        1. Check if translation/transliteration is required based on script/language mismatch.
        2. Standardize names to match the portal options/style if mismatch exists, or return them unchanged if they match portal expectations.
        3. Format search variables exactly.
        
        Return a clean JSON matching the input keys.
        """
        
        response = LLMClient.call_llm(prompt, system_instruction=system_instruction, json_mode=True)
        return json.loads(response)
