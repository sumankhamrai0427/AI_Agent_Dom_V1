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
           - For 'ELECTRICITY': Compare owner/customer name, consumer_id, and installation_no.
             CRITICAL MONTH MATCHING RULE: The portal dataset may contain a 'bill_history' list showing records for multiple past months. You MUST look for a billing month in 'bill_history' that matches the document's 'bill_month' (e.g. matching 'MAY-2026' with 'MAY,2026' or 'MAY 2026'). If you find a matching month, compare the document's 'bill_amount' against the 'amount_before_due' or amount for that specific month in the history. If they match, mark it as a MATCH rather than a mismatch. Only if the month is missing from the history or the amount is different should you report a mismatch.
        4. Determine if the record is overall valid (is_valid: true/false).
           - For 'ELECTRICITY': If the key customer identifiers (Consumer ID, Installation Number, and Customer Name) match after normalization, 'is_valid' MUST be true. A difference in the current bill amount or month (due to old bills vs new bills) should be noted in the conflicts list, but it does NOT make the record invalid.
           - For 'LAND': If the owner name and Khata/Plot number match after normalization, 'is_valid' MUST be true. Minor differences in area or father's name spelling should be noted in conflicts, but they do NOT make the record invalid.
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
            core_conflicts = []
            
            if utility_type == "ELECTRICITY":
                doc_cons = str(document_data.get("consumer_id", "")).strip()
                port_cons = str(portal_data.get("consumer_id", "")).strip()
                if doc_cons != port_cons:
                    msg = f"Consumer ID mismatch: Document has '{doc_cons}', Portal has '{port_cons}'"
                    core_conflicts.append(msg)
                    conflicts.append(msg)
                
                doc_inst = str(document_data.get("installation_no", "")).strip()
                port_inst = str(portal_data.get("installation_no", "")).strip()
                if doc_inst != port_inst:
                    msg = f"Installation No mismatch: Document has '{doc_inst}', Portal has '{port_inst}'"
                    core_conflicts.append(msg)
                    conflicts.append(msg)
                    
                doc_owner = str(document_data.get("owner_name", "")).strip().upper()
                port_owner = str(portal_data.get("owner_name", "")).strip().upper()
                if doc_owner and port_owner and doc_owner not in port_owner and port_owner not in doc_owner:
                    msg = f"Owner/Customer Name mismatch: Document has '{doc_owner}', Portal has '{port_owner}'"
                    core_conflicts.append(msg)
                    conflicts.append(msg)
                
                doc_amount = str(document_data.get("bill_amount", "")).strip()
                doc_month = str(document_data.get("bill_month", "")).strip().upper()
                
                # Check if there is a match in bill_history
                bill_history = portal_data.get("bill_history", []) if isinstance(portal_data.get("bill_history"), list) else []
                matched_history = False
                matched_amount = None
                
                # Normalize doc_month to match formats (e.g. "MAY-2026", "MAY,2026", "MAY2026")
                clean_doc_month = "".join(c for c in doc_month if c.isalnum())
                
                for bill in bill_history:
                    bill_mo = str(bill.get("bill_month", "")).strip().upper()
                    clean_bill_mo = "".join(c for c in bill_mo if c.isalnum())
                    if clean_doc_month in clean_bill_mo or clean_bill_mo in clean_doc_month:
                        matched_history = True
                        matched_amount = str(bill.get("amount_before_due", "")).strip()
                        break
                
                if matched_history:
                    # Compare against the historical record amount
                    if doc_amount != matched_amount:
                        conflicts.append(f"Bill amount mismatch for {doc_month}: Document has '{doc_amount}', Portal history has '{matched_amount}'")
                else:
                    # Fallback to comparing with latest
                    port_amount = str(portal_data.get("bill_amount", "")).strip()
                    port_month = str(portal_data.get("bill_month", "")).strip().upper()
                    if doc_amount != port_amount:
                        conflicts.append(f"Bill amount mismatch: Document has '{doc_amount}', Portal has '{port_amount}'")
                    if doc_month != port_month:
                        conflicts.append(f"Bill month mismatch: Document has '{doc_month}', Portal has '{port_month}'")

                return {
                    "is_valid": len(core_conflicts) == 0,
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
                        "bill_amount": doc_amount,
                        "bill_month": doc_month
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
                        msg = "Owner record not found on Portal."
                        core_conflicts.append(msg)
                        conflicts.append(msg)
                    else:
                        msg = f"Owner Name discrepancy: Deed has '{doc_owner}', Portal has '{port_owner}'"
                        core_conflicts.append(msg)
                        conflicts.append(msg)
                    
                doc_khata = str(document_data.get("khata", "")).strip()
                port_khata = str(portal_data.get("khata", "")).strip()
                if doc_khata != port_khata:
                    if not port_khata:
                        msg = "Khata record not found on Portal."
                        core_conflicts.append(msg)
                        conflicts.append(msg)
                    else:
                        msg = f"Khata number mismatch: Deed has '{doc_khata}', Portal has '{port_khata}'"
                        core_conflicts.append(msg)
                        conflicts.append(msg)
                    
                return {
                    "is_valid": len(core_conflicts) == 0,
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
        
