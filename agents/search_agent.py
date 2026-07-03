from utils.config import get_portal_config
from utils.logger import logger

class SearchAgent:
    @staticmethod
    def identify_portal(state, district=None):
        logger.info(f"Search Agent mapping portal for State: '{state}', District: '{district}'")
        
        config = get_portal_config(state)
        
        search_task = {
            "state": state.upper(),
            "portal_name": config["name"],
            "url": config["url"],
            "selectors": config["selectors"]
        }
        
        logger.info(f"Target Portal identified: '{config['name']}' at {config['url']}")
        return search_task
