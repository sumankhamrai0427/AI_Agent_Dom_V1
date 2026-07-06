import json
from helpers.llm_client import LLMClient
from utils.logger import logger

# Agent type keyword detection
SHARE_MARKET_KEYWORDS = ["share market", "stock", "nse", "bse", "equity", "trading"]
KMC_KEYWORDS = ["kolkata municipal", "kmc", "municipality"]
ELECTRICITY_KEYWORDS = ["electricity", "electric bill", "wbsedcl", "power bill"]
LAND_KEYWORDS = ["land", "deed", "khata", "khasra", "bhumi", "ownership"]


def detect_agent_type(objective: str) -> str:
    """Detect the agent type from the task objective string."""
    obj_lower = objective.lower()
    if any(kw in obj_lower for kw in SHARE_MARKET_KEYWORDS):
        return "SHARE_MARKET"
    if any(kw in obj_lower for kw in KMC_KEYWORDS):
        return "KMC"
    if any(kw in obj_lower for kw in ELECTRICITY_KEYWORDS):
        return "ELECTRICITY"
    return "LAND"


class PlannerAgent:
    @staticmethod
    def create_plan(objective):
        logger.info(f"Planner Agent generating execution plan for objective: '{objective}'")

        agent_type = detect_agent_type(objective)
        logger.info(f"Detected agent type: {agent_type}")

        # --- Share Market Agent: fixed lightweight plan ---
        if agent_type == "SHARE_MARKET":
            return [
                {"id": 1, "task": "Search Stock Portal", "status": "PENDING"},
                {"id": 2, "task": "Extract Stock Data", "status": "PENDING"},
                {"id": 3, "task": "Analyze Market Trends", "status": "PENDING"},
                {"id": 4, "task": "Generate Final Report", "status": "PENDING"},
            ]

        # --- Kolkata Municipal Corporation Agent: fixed plan ---
        if agent_type == "KMC":
            return [
                {"id": 1, "task": "Search KMC Portal", "status": "PENDING"},
                {"id": 2, "task": "Extract Property Records", "status": "PENDING"},
                {"id": 3, "task": "Verify Findings", "status": "PENDING"},
                {"id": 4, "task": "Generate Final Report", "status": "PENDING"},
            ]

        # --- Land / Electricity: standard LLM-driven plan ---
        system_instruction = """
        You are a Senior Planner Agent. Analyze the user's objective and break it down into sequential, atomic tasks.
        You MUST select your descriptive step names ("task") ONLY from the following list of standard workflow steps:
        - "Extract Document Data"
        - "Validate Extracted Data"
        - "Search Government Portal"
        - "Extract Land Records"
        - "Verify Findings"
        - "Retrieve GIS Coordinates"
        - "Generate Final Report"
        
        Do not create custom step names outside this list, otherwise the supervisor agent will not be able to execute them.
        
        Output MUST be a JSON array of task objects, each containing:
        - "id": unique integer
        - "task": descriptive step name from the standard list
        - "status": "PENDING"
        
        Example output format:
        [
          {"id": 1, "task": "Extract Document Data", "status": "PENDING"},
          {"id": 2, "task": "Validate Extracted Data", "status": "PENDING"},
          {"id": 3, "task": "Search Government Portal", "status": "PENDING"},
          {"id": 4, "task": "Extract Land Records", "status": "PENDING"},
          {"id": 5, "task": "Verify Findings", "status": "PENDING"},
          {"id": 6, "task": "Retrieve GIS Coordinates", "status": "PENDING"},
          {"id": 7, "task": "Generate Final Report", "status": "PENDING"}
        ]
        """
        
        prompt = f"Break down the following objective into a structured workflow task list:\nObjective: '{objective}'"
        
        try:
            response = LLMClient.call_llm(prompt, system_instruction=system_instruction, json_mode=True)
            plan = json.loads(response)
            
            # Ensure it is a list
            if isinstance(plan, dict):
                for val in plan.values():
                    if isinstance(val, list):
                        plan = val
                        break
                else:
                    plan = [plan]
            
            # Validate plan structure and length
            if not isinstance(plan, list) or len(plan) < 3:
                raise ValueError("Plan has insufficient steps or is not a list")
                
            for step in plan:
                if not isinstance(step, dict) or "task" not in step:
                    raise ValueError("Plan step is missing 'task' key")
            
            logger.info(f"Plan generated successfully: {plan}")
            return plan
        except Exception as e:
            logger.error(f"Planner Agent failed or returned invalid plan: {e}. Returning default execution plan.")
            # Default fallback workflow containing all 7 steps
            return [
                {"id": 1, "task": "Extract Document Data", "status": "PENDING"},
                {"id": 2, "task": "Validate Extracted Data", "status": "PENDING"},
                {"id": 3, "task": "Search Government Portal", "status": "PENDING"},
                {"id": 4, "task": "Extract Land Records", "status": "PENDING"},
                {"id": 5, "task": "Verify Findings", "status": "PENDING"},
                {"id": 6, "task": "Retrieve GIS Coordinates", "status": "PENDING"},
                {"id": 7, "task": "Generate Final Report", "status": "PENDING"}
            ]
