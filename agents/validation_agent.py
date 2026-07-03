import json
from helpers.llm_client import LLMClient
from utils.logger import logger

class ValidationAgent:
    @staticmethod
    def validate_records(document_data, portal_data):
        logger.info("Validation Agent starting record comparisons...")
        
        system_instruction = """
        You are a Data Validation Specialist. Compare the extracted document/bill records against the live portal data.
        
        Perform the following tasks:
        1. Identify the 'utility_type' from the document dataset ("LAND" or "ELECTRICITY").
        2. Normalize strings (trim spacing, uppercase names).
        3. Identify matches and discrepancies:
           - For 'LAND': Compare owner name, father's name, village, district, khata, khasra, area.
           - For 'ELECTRICITY': Compare owner/customer name, consumer_id, installation_no, bill_amount, bill_month.
        4. Determine if the record is overall valid (is_valid: true/false). If names and key identifiers (Khata or Consumer ID) match after normalization, it should be true.
        5. List any conflicts (mismatches) clearly.
        6. Provide a normalized output dataset.
        
        Output MUST be a JSON object of format:
        {
          "is_valid": true,
          "conflicts": [],
          "normalized_data": {
             "owner_name": "RAMESH KUMAR",
             "father_name": "SURESH KUMAR", // or null for electricity
             "village": "BARA", // or null/address for electricity
             "district": "VARANASI",
             "khata": "452", // or null for electricity
             "khasra": "120", // or null for electricity
             "area": "1.25 Hectares", // or null for electricity
             "consumer_id": null, // or value for electricity
             "installation_no": null // or value for electricity
          }
        }
        """
        
        prompt = f"""
        Compare the following datasets:
        
        Document Dataset:
        {json.dumps(document_data, indent=2)}
        
        Portal Dataset:
        {json.dumps(portal_data, indent=2)}
        """
        
        try:
            response = LLMClient.call_llm(prompt, system_instruction=system_instruction, json_mode=True)
            results = json.loads(response)
            logger.info(f"Validation verification complete. Valid: {results.get('is_valid')}")
            return results
        except Exception as e:
            logger.error(f"Validation Agent failed: {e}. Executing manual programmatic validation.")
            
            utility_type = document_data.get("utility_type", "LAND")
            conflicts = []
            
            if utility_type == "ELECTRICITY":
                doc_cons = str(document_data.get("consumer_id", "")).strip()
                port_cons = str(portal_data.get("consumer_id", "")).strip()
                if doc_cons != port_cons:
                    conflicts.append(f"Consumer ID mismatch: Document has '{doc_cons}', Portal has '{port_cons}'")
                
                doc_inst = str(document_data.get("installation_no", "")).strip()
                port_inst = str(portal_data.get("installation_no", "")).strip()
                if doc_inst != port_inst:
                    conflicts.append(f"Installation No mismatch: Document has '{doc_inst}', Portal has '{port_inst}'")
                    
                doc_owner = str(document_data.get("owner_name", "")).strip().upper()
                port_owner = str(portal_data.get("owner_name", "")).strip().upper()
                if doc_owner and port_owner and doc_owner not in port_owner and port_owner not in doc_owner:
                    conflicts.append(f"Owner/Customer Name mismatch: Document has '{doc_owner}', Portal has '{port_owner}'")
                
                return {
                    "is_valid": len(conflicts) == 0,
                    "conflicts": conflicts,
                    "normalized_data": {
                        "owner_name": doc_owner if port_owner else doc_owner,
                        "father_name": None,
                        "village": str(document_data.get("village", "")).strip().upper(),
                        "district": str(document_data.get("district", "")).strip().upper(),
                        "khata": None,
                        "khasra": None,
                        "area": None,
                        "consumer_id": doc_cons,
                        "installation_no": doc_inst,
                        "bill_amount": str(document_data.get("bill_amount", "")).strip()
                    }
                }
            else:
                # Programmatic fallback logic for LAND
                doc_owner = str(document_data.get("owner_name", "")).strip().upper()
                port_owner = str(portal_data.get("owner_name", "")).strip().upper()
                
                # Simple fuzzy matching (containment, checking non-emptiness)
                name_match = False
                if doc_owner and port_owner:
                    name_match = (doc_owner in port_owner) or (port_owner in doc_owner)
                
                if not name_match:
                    if not port_owner:
                        conflicts.append("Owner record not found on Portal.")
                    else:
                        conflicts.append(f"Owner Name discrepancy: Deed has '{doc_owner}', Portal has '{port_owner}'")
                    
                doc_khata = str(document_data.get("khata", "")).strip()
                port_khata = str(portal_data.get("khata", "")).strip()
                if doc_khata != port_khata:
                    if not port_khata:
                        conflicts.append("Khata record not found on Portal.")
                    else:
                        conflicts.append(f"Khata number mismatch: Deed has '{doc_khata}', Portal has '{port_khata}'")
                    
                return {
                    "is_valid": len(conflicts) == 0,
                    "conflicts": conflicts,
                    "normalized_data": {
                        "owner_name": doc_owner if name_match else (f"{doc_owner} / {port_owner}" if port_owner else doc_owner),
                        "father_name": str(document_data.get("father_name", "")).strip().upper(),
                        "village": str(document_data.get("village", "")).strip().upper(),
                        "district": str(document_data.get("district", "")).strip().upper(),
                        "khata": doc_khata,
                        "khasra": str(document_data.get("khasra", "")).strip(),
                        "area": str(document_data.get("area", "")).strip(),
                        "consumer_id": None,
                        "installation_no": None
                    }
                }
        
