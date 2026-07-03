import asyncio
import os
import traceback
from utils.logger import logger
from repositories.task_repository import TaskRepository
from repositories.agent_log_repository import AgentLogRepository
from agents.planner_agent import PlannerAgent
from agents.document_agent import DocumentAgent
from agents.search_agent import SearchAgent
from agents.browser_agent import BrowserAgent
from agents.validation_agent import ValidationAgent
from services.gis_processor import GISProcessor
from services.pdf_service import PDFService

class SupervisorAgent:
    def __init__(self, task_id):
        self.task_id = task_id
        self.repository = TaskRepository()
        self.log_repository = AgentLogRepository()

    async def execute_workflow(self):
        logger.info(f"Supervisor Agent commencing workflow for Task #{self.task_id}")
        
        # 1. Update status to RUNNING / PLANNING
        self.repository.update_status(self.task_id, status="RUNNING", current_step="Planning workflow")
        
        task = self.repository.get_task(self.task_id)
        if not task:
            logger.error(f"Task #{self.task_id} not found in database.")
            return

        metadata = task.get_metadata()
        objective = task.objective
        
        # Log planning start
        self.log_repository.log_action(
            task_id=self.task_id,
            agent_name="SupervisorAgent",
            step_name="Workflow Planning",
            action="plan",
            result="Generating plan",
            status="SUCCESS"
        )
        
        # 2. Get Execution Plan
        plan_steps = PlannerAgent.create_plan(objective)
        self.repository.update_status(self.task_id, current_step="Plan created")
        
        document_data = {}
        portal_data = {}
        validation_results = {}
        gis_results = {}
        report_files = []
        
        step_index = 0
        
        try:
            for step in plan_steps:
                step_name = step["task"]
                step_index += 1
                logger.info(f"Supervisor executing Step {step_index}: '{step_name}'")
                self.repository.update_status(self.task_id, current_step=f"Running: {step_name}")
                
                # Retry wrapper for each step
                max_retries = 3
                retry_count = 0
                step_success = False
                error_message = ""

                while retry_count < max_retries and not step_success:
                    try:
                        if "Extract Document Data" in step_name:
                            doc_path = metadata.get("document_path")
                            if doc_path and os.path.exists(doc_path):
                                document_data = DocumentAgent.process_document(doc_path)
                            else:
                                logger.warning("No document file uploaded. Skipping document extraction step.")
                                # Default placeholder structure if no document provided
                                document_data = {
                                    "owner_name": metadata.get("owner_name", "RAMESH KUMAR"),
                                    "father_name": metadata.get("father_name", "SURESH KUMAR"),
                                    "village": metadata.get("village", "BARA"),
                                    "district": metadata.get("district", "VARANASI"),
                                    "khata": metadata.get("khata", "452"),
                                    "khasra": metadata.get("khasra", "120"),
                                    "area": metadata.get("area", "1.25 Hectares"),
                                    "reference_number": "N/A"
                                }
                            # Save to Database
                            self.repository.save_document_record(self.task_id, document_data)
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="DocumentAgent",
                                step_name=step_name,
                                action="extract_document",
                                result=f"Owner: {document_data.get('owner_name')}, Khata: {document_data.get('khata')}",
                                status="SUCCESS"
                            )
                            step_success = True

                        elif "Validate Extracted Data" in step_name:
                            utility_type = document_data.get("utility_type", "LAND")
                            if utility_type == "ELECTRICITY":
                                required_fields = ["consumer_id", "installation_no"]
                            else:
                                required_fields = ["district", "village", "khata"]
                                
                            missing = [f for f in required_fields if not document_data.get(f)]
                            if missing:
                                err_msg = f"Required fields missing from input data: {', '.join(missing)}."
                                if utility_type == "LAND" and not document_data.get("district") and not document_data.get("village"):
                                    err_msg += " This usually happens because the uploaded document is a scanned PDF/image, and the Gemini OCR API key has exceeded its daily quota (429 Resource Exhausted), resulting in empty text."
                                raise ValueError(err_msg)
                            
                            # Standardize values
                            if utility_type == "ELECTRICITY":
                                document_data["consumer_id"] = str(document_data.get("consumer_id", "")).strip()
                                document_data["installation_no"] = str(document_data.get("installation_no", "")).strip()
                                document_data["district"] = str(document_data.get("district", "") or "WB").strip().upper()
                            else:
                                document_data["district"] = str(document_data.get("district", "")).strip().upper()
                                document_data["village"] = str(document_data.get("village", "")).strip().upper()
                                document_data["khata"] = str(document_data.get("khata", "")).strip()
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="ValidationAgent",
                                step_name=step_name,
                                action="validate_input",
                                result="Input values standardized and complete.",
                                status="SUCCESS"
                            )
                            step_success = True

                        elif "Search Government Portal" in step_name:
                            # Map State/District to Government Portal
                            state = metadata.get("state", "UP")
                            utility_type = document_data.get("utility_type", "LAND")
                            
                            if utility_type == "ELECTRICITY":
                                # Detect if it is a West Bengal/WBSEDCL bill to override default dropdown mismatches
                                doc_fields = [
                                    str(document_data.get("village") or ""),
                                    str(document_data.get("district") or ""),
                                    str(document_data.get("owner_name") or ""),
                                    str(document_data.get("reference_number") or "")
                                ]
                                doc_text = " ".join(doc_fields).lower()
                                
                                is_wb = any(kw in doc_text for kw in ["wb", "wbsedcl", "west bengal", "burdwan", "hooghly", "baruipara", "bidhan pally"])
                                if is_wb or state == "WB":
                                    state_key = "WB_ELECTRICITY"
                                else:
                                    state_key = f"{state}_ELECTRICITY"
                            else:
                                state_key = state
                                
                            portal_task = SearchAgent.identify_portal(state_key, document_data.get("district"))
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="SearchAgent",
                                step_name=step_name,
                                action="map_portal",
                                url=portal_task["url"],
                                result=f"Mapped state portal: {portal_task['portal_name']}",
                                status="SUCCESS"
                            )
                            
                            # Trigger Autonomous Browser Agent
                            browser_agent = BrowserAgent(self.task_id, self.repository, self.log_repository)
                            
                            if utility_type == "ELECTRICITY":
                                goal_desc = (
                                    f"Search and view electricity bill in {portal_task['portal_name']} portal. "
                                    f"IMPORTANT search sequence: "
                                    f"1. First, enter the Consumer ID '{document_data.get('consumer_id')}' in the Consumer Id input field. "
                                    f"2. Second, enter the Installation ID '{document_data.get('installation_no')}' in the Installation Number input field. "
                                    f"3. Third, solve the Captcha challenge and wait. "
                                    f"4. Fourth, click the View Bill or Submit button to display the bill details. "
                                    f"5. Fifth, once the bill details are loaded, extract the bill customer name, bill month, and bill amount."
                                )
                                search_params = {
                                    "consumer_id": document_data.get("consumer_id"),
                                    "installation_no": document_data.get("installation_no"),
                                    "owner_name": document_data.get("owner_name")
                                }
                            else:
                                goal_desc = (
                                    f"Search land records in {portal_task['portal_name']} portal. "
                                    f"IMPORTANT search sequence: "
                                    f"1. First, select District matching '{document_data.get('district')}' (District code: '{document_data.get('district_code')}') from dropdown. "
                                    f"2. Second, select Tehsil matching '{document_data.get('tehsil')}' (Tehsil code: '{document_data.get('tehsil_code')}') from dropdown. "
                                    f"3. Third, select Village matching '{document_data.get('village')}' (Village code: '{document_data.get('village_code')}') from dropdown. "
                                    f"4. Fourth, enter Khata/Plot number '{document_data.get('khata')}' in text input and click search."
                                )
                                search_params = {
                                    "district": document_data.get("district"),
                                    "district_code": document_data.get("district_code"),
                                    "tehsil": document_data.get("tehsil"),
                                    "tehsil_code": document_data.get("tehsil_code"),
                                    "village": document_data.get("village"),
                                    "village_code": document_data.get("village_code"),
                                    "khata": document_data.get("khata"),
                                    "owner_name": document_data.get("owner_name")
                                }
                            
                            # Run browser observation loop
                            portal_data = await browser_agent.run_search_workflow(
                                goal=goal_desc,
                                start_url=portal_task["url"],
                                search_params=search_params
                            )
                            step_success = True

                        elif "Verify Findings" in step_name:
                            validation_results = ValidationAgent.validate_records(document_data, portal_data)
                            
                            # Save verification result to DB
                            self.repository.save_verification_result(
                                self.task_id,
                                is_valid=validation_results.get("is_valid", True),
                                conflicts=validation_results.get("conflicts", []),
                                normalized_data=validation_results.get("normalized_data", {})
                            )
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="ValidationAgent",
                                step_name=step_name,
                                action="verify_match",
                                result=f"Verification complete. Valid match: {validation_results.get('is_valid')}",
                                status="SUCCESS" if validation_results.get("is_valid") else "WARNING"
                            )
                            step_success = True

                        elif "Retrieve GIS Coordinates" in step_name:
                            utility_type = document_data.get("utility_type", "LAND")
                            if utility_type == "ELECTRICITY":
                                logger.info("Electricity bill task. Skipping actual GIS retrieval and saving empty GIS record.")
                                gis_results = {}
                                self.repository.save_gis_record(
                                    self.task_id,
                                    geojson="{}",
                                    kml="",
                                    adjacent_plots="[]",
                                    coordinate_system="N/A",
                                    map_html_path=""
                                )
                            else:
                                khata = document_data.get("khata", "452")
                                village = document_data.get("village", "BARA")
                                district = document_data.get("district", "VARANASI")
                                
                                gis_results = GISProcessor.process_plot_gis(self.task_id, khata, village, district)
                                
                                self.repository.save_gis_record(
                                    self.task_id,
                                    geojson=gis_results["geojson_path"],
                                    kml=gis_results["kml_path"],
                                    adjacent_plots=gis_results["adjacent_plots"],
                                    coordinate_system=gis_results["utm_zone"],
                                    map_html_path=gis_results["map_html_path"]
                                )
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="GISAgent",
                                step_name=step_name,
                                action="gis_boundary_generation",
                                result="Electricity details processed." if utility_type == "ELECTRICITY" else f"Coordinates system: {gis_results['utm_zone']}. Centroid: {gis_results['centroid']}",
                                status="SUCCESS"
                            )
                            step_success = True

                        elif "Generate Final Report" in step_name:
                            # Assemble final pdf and excel packages
                            report_dir = "storage/reports"
                            
                            report_data = {
                                "state": metadata.get("state", "UP"),
                                "document": document_data,
                                "portal": portal_data,
                                "verification": validation_results
                            }
                            
                            # Retrieve step logs
                            logs = self.log_repository.get_logs_for_task(self.task_id)
                            
                            xlsx_path = os.path.join(report_dir, f"report_{self.task_id}_audit.xlsx")
                            html_path = os.path.join(report_dir, f"report_{self.task_id}_summary.html")
                            
                            sheet_path = PDFService.generate_excel_report(self.task_id, report_data, logs, xlsx_path)
                            summary_path = PDFService.generate_html_report(self.task_id, report_data, logs, gis_results, html_path)
                            
                            # Log finalized files
                            metadata["excel_report"] = sheet_path
                            metadata["html_report"] = summary_path
                            self.repository.update_status(self.task_id, current_step="Report generated")
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="ReportAgent",
                                step_name=step_name,
                                action="generate_reports",
                                result=f"Compiled Excel and Interactive HTML report at {report_dir}",
                                status="SUCCESS"
                            )
                            step_success = True
                            
                        else:
                            # Generic task success fallback
                            logger.info(f"Executing step placeholder: '{step_name}'")
                            await asyncio.sleep(0.5)
                            step_success = True

                    except Exception as e:
                        retry_count += 1
                        error_message = str(e)
                        tb = traceback.format_exc()
                        logger.error(f"Step '{step_name}' failed. Retry {retry_count}/{max_retries}. Error: {error_message}\n{tb}")
                        
                        self.log_repository.log_action(
                            task_id=self.task_id,
                            agent_name="SupervisorAgent",
                            step_name=step_name,
                            action="retry",
                            error_message=f"Attempt {retry_count} failed: {error_message}",
                            retry_count=retry_count,
                            status="RETRYING"
                        )
                        
                        await asyncio.sleep(2) # Backoff
                
                if not step_success:
                    raise RuntimeError(f"Step '{step_name}' failed permanently after {max_retries} attempts. Last error: {error_message}")

            # 3. Complete Task
            # Fetch final metadata
            task_instance = self.repository.get_task(self.task_id)
            task_instance.set_metadata(metadata)
            self.repository.update_status(self.task_id, status="COMPLETED", current_step="Workflow complete")
            
            self.log_repository.log_action(
                task_id=self.task_id,
                agent_name="SupervisorAgent",
                step_name="Execution End",
                action="complete",
                result="Land record verification successfully finalized.",
                status="SUCCESS"
            )

        except Exception as workflow_error:
            tb = traceback.format_exc()
            logger.error(f"Workflow failed for Task #{self.task_id}: {workflow_error}\n{tb}")
            
            self.repository.update_status(
                self.task_id, 
                status="FAILED", 
                error_message=str(workflow_error)
            )
            
            self.log_repository.log_action(
                task_id=self.task_id,
                agent_name="SupervisorAgent",
                step_name="Workflow Failure",
                action="terminate",
                error_message=str(workflow_error),
                status="FAILURE"
            )
        
        finally:
            self.repository.close()
            self.log_repository.close()
