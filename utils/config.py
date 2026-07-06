import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Portals mapping
PORTAL_MAPPING = {
    "UP": {
        "name": "Bhu Naksha UP",
        "url": "https://upbhunaksha.gov.in/",
        "selectors": {
            "district_select": "#district_list",
            "tehsil_select": "#tehsil_list",
            "village_select": "#village_list",
            "khata_input": "#khata_no",
            "search_btn": "#search_button",
            "captcha_img": "#captcha_image",
            "result_table": "#result_table"
        }
    },
    "BIHAR": {
        "name": "Bihar Bhumi",
        "url": "http://biharbhumi.bihar.gov.in",
        "selectors": {
            "district_select": "#district",
            "tehsil_select": "#anchal",
            "village_select": "#mauja",
            "khata_input": "#khata",
            "search_btn": "#search",
            "captcha_img": "#captcha",
            "result_table": "#result"
        }
    },
    "WB": {
        "name": "Banglarbhumi",
        "url": "https://banglarbhumi.gov.in",
        "selectors": {
            "district_select": "#ddldistrict",
            "tehsil_select": "#ddlblk",
            "village_select": "#ddlmouza",
            "khata_input": "#khataNo",
            "search_btn": "#btnSearch",
            "captcha_img": "#captchaCode",
            "result_table": "#detailsTable"
        }
    },
    "WB_ELECTRICITY": {
        "name": "WBSEDCL View Bill",
        "url": "https://portal.wbsedcl.in/webdynpro/resources/wbsedcl/viewbillwl/WBViewBillWL",
        "selectors": {
            "consumer_input": "input[id='BIEI.WBViewBillWLCompView.InputField']",
            "installation_input": "input[id='BIEI.WBViewBillWLCompView.InputField1']",
            "captcha_input": "input[id='BIEI.WBViewBillWLCompView.InputField2']",
            "search_btn": "[id='BIEI.WBViewBillWLCompView.Button']"
        }
    },
    "STOCK_MARKET": {
        "name": "Google Finance",
        "url": "https://www.google.com/finance/quote/{symbol}:NSE",
        "selectors": {
            "price": "div.YMlKec.fxKbKc",
            "change": "div.P6K39c",
            "name": "div.zzDege"
        }
    }
}

DEFAULT_PORTAL = {
    "name": "Mock National Land Portal",
    "url": "https://mocklandrecords.gov.in",
    "selectors": {
        "district_select": "#district-select",
        "tehsil_select": "#tehsil-select",
        "village_select": "#village-select",
        "khata_input": "#khata-input",
        "search_btn": "#search-btn",
        "captcha_img": "#captcha-container img",
        "result_table": "#records-grid"
    }
}

def get_portal_config(state):
    return PORTAL_MAPPING.get(state.upper(), DEFAULT_PORTAL)

# API Keys
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "demo")

# Local Mistral configs
ACTIVE_LLM = os.getenv("ACTIVE_LLM", "gemini")
MISTRAL_LOCAL_URL = os.getenv("MISTRAL_LOCAL_URL", "http://localhost:11434")
MISTRAL_LOCAL_MODEL = os.getenv("MISTRAL_LOCAL_MODEL", "mistral-small:24b")

# LLM Models
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Storage configs
STORAGE_DIR = "storage"
SCREENSHOT_DIR = os.path.join(STORAGE_DIR, "screenshots")
REPORT_DIR = os.path.join(STORAGE_DIR, "reports")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")

for path in [SCREENSHOT_DIR, REPORT_DIR, UPLOAD_DIR]:
    os.makedirs(path, exist_ok=True)
