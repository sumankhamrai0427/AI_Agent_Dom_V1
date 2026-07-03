import pytest
import os
import json
from agents.planner_agent import PlannerAgent
from agents.validation_agent import ValidationAgent
from agents.search_agent import SearchAgent
from services.gis_processor import GISProcessor
from services.ocr_service import OCRService
from models.models import init_db, Task, SessionLocal

# Initialize Database for testing
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()
    yield

def test_planner_agent():
    objective = "Verify ownership for Khata 452 in Varanasi, UP"
    plan = PlannerAgent.create_plan(objective)
    
    assert isinstance(plan, list)
    assert len(plan) > 0
    assert "task" in plan[0]
    assert any("Search Government Portal" in item["task"] for item in plan)

def test_validation_agent():
    doc_data = {
        "owner_name": "Ramesh Kumar",
        "father_name": "Suresh Kumar",
        "village": "Bara",
        "district": "Varanasi",
        "khata": "452",
        "khasra": "120"
    }
    
    # 1. Matching records
    portal_data_match = {
        "owner_name": "RAMESH KUMAR",
        "father_name": "SURESH KUMAR",
        "village": "Bara",
        "district": "Varanasi",
        "khata": "452",
        "khasra": "120"
    }
    res_match = ValidationAgent.validate_records(doc_data, portal_data_match)
    assert res_match["is_valid"] is True
    assert len(res_match["conflicts"]) == 0
    
    # 2. Conflicting records
    portal_data_conflict = {
        "owner_name": "Dinesh Kumar",
        "father_name": "Suresh Kumar",
        "village": "Bara",
        "district": "Varanasi",
        "khata": "452",
        "khasra": "120"
    }
    res_conflict = ValidationAgent.validate_records(doc_data, portal_data_conflict)
    assert res_conflict["is_valid"] is False
    assert len(res_conflict["conflicts"]) > 0

def test_search_agent():
    portal = SearchAgent.identify_portal("UP")
    assert portal["state"] == "UP"
    assert "bhulekh" in portal["url"].lower() or "bhunaksha" in portal["url"].lower()
    assert "district_select" in portal["selectors"]

def test_gis_processor():
    # Centroid coordinate conversions
    x, y = 700000, 2800000
    lon, lat = GISProcessor.convert_coordinates(x, y, "EPSG:32644", "EPSG:4326")
    assert isinstance(lon, float)
    assert isinstance(lat, float)
    
    # Check shape generation
    gis_res = GISProcessor.process_plot_gis(task_id=999, khata="452", village="BARA", district="VARANASI")
    assert os.path.exists(gis_res["geojson_path"])
    assert os.path.exists(gis_res["kml_path"])
    assert os.path.exists(gis_res["csv_path"])
    assert os.path.exists(gis_res["map_html_path"])
    
    # Clean up test output
    for path in ["geojson_path", "kml_path", "csv_path", "map_html_path"]:
        if os.path.exists(gis_res[path]):
            os.remove(gis_res[path])

def test_ocr_service_fallback():
    # If no file exists, assert exception
    with pytest.raises(FileNotFoundError):
        OCRService.extract_text_from_pdf("nonexistent.pdf")
