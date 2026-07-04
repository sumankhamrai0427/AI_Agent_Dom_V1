import threading
import asyncio
from repositories.task_repository import TaskRepository
from repositories.agent_log_repository import AgentLogRepository
from agents.supervisor_agent import SupervisorAgent
from utils.logger import logger

class TaskService:
    def __init__(self):
        self.repository = TaskRepository()
        self.log_repository = AgentLogRepository()

    def create_search_task(self, objective, metadata=None):
        logger.info(f"Service triggering new search task: objective='{objective}'")
        
        # Proactively cancel any previous active tasks to release browser sessions
        try:
            from models.models import Task
            active_tasks = self.repository.session.query(Task).filter(Task.status.in_(["RUNNING", "PAUSED_CAPTCHA", "PENDING"])).all()
            for t in active_tasks:
                logger.info(f"Cancelling previous running/paused task #{t.id} to avoid conflicts.")
                t.status = "FAILED"
                t.error_message = "Task cancelled because a new task was started."
            self.repository.commit()
        except Exception as e:
            logger.warning(f"Failed to cancel previous tasks: {e}")
            
        task = self.repository.create_task(objective, metadata)
        
        # Spawn Supervisor workflow in a background thread to prevent Flask blocking
        thread = threading.Thread(
            target=self._run_supervisor_background,
            args=(task.id,),
            daemon=True
        )
        thread.start()
        
        return task

    def _run_supervisor_background(self, task_id):
        logger.info(f"Background thread started for Task #{task_id}")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            supervisor = SupervisorAgent(task_id)
            loop.run_until_complete(supervisor.execute_workflow())
        except Exception as e:
            logger.error(f"Background supervisor task failed: {e}")
        finally:
            loop.close()
            logger.info(f"Background thread ended for Task #{task_id}")

    def get_task_details(self, task_id):
        task = self.repository.get_task(task_id)
        if not task:
            return None
            
        logs = self.log_repository.get_logs_for_task(task_id)
        
        # Format logs for frontend output
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "agent_name": log.agent_name,
                "step_name": log.step_name,
                "action": log.action,
                "url": log.url,
                "result": log.result,
                "screenshot_url": f"/api/storage/screenshots/{log.screenshot_path.split(chr(92))[-1]}" if log.screenshot_path else None,
                "execution_time_ms": log.execution_time_ms,
                "error_message": log.error_message,
                "status": log.status
            })
            
        # Get documents/GIS records
        doc_record = task.documents[0].get_raw_data() if task.documents else None
        gis_record = {
            "adjacent_plots": task.gis_records[0].adjacent_plots_json if task.gis_records else "[]",
            "centroid": task.gis_records[0].coordinate_system if task.gis_records else "",
            "map_html_url": f"/storage/reports/plot_{task.id}_map.html" if task.gis_records else None
        } if task.gis_records else None

        verification = {
            "is_valid": task.verifications[0].is_valid,
            "conflicts": task.verifications[0].conflicts,
            "normalized_data": task.verifications[0].normalized_data_json
        } if task.verifications else None

        return {
            "id": task.id,
            "objective": task.objective,
            "status": task.status,
            "current_step": task.current_step,
            "error_message": task.error_message,
            "metadata": task.get_metadata(),
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "logs": formatted_logs,
            "extracted_document": doc_record,
            "gis_data": gis_record,
            "verification": verification
        }

    def get_all_tasks(self):
        tasks = self.repository.get_all_tasks()
        return [{
            "id": t.id,
            "objective": t.objective,
            "status": t.status,
            "current_step": t.current_step,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for t in tasks]

    def solve_captcha(self, task_id):
        logger.info(f"Signal received to resume Task #{task_id} after CAPTCHA solution.")
        # Change status back to RUNNING to trigger the BrowserAgent loop wait condition
        task = self.repository.update_status(task_id, status="RUNNING", current_step="Resuming after CAPTCHA")
        return task is not None

    def get_task_document_data(self, task_id):
        task = self.repository.get_task(task_id)
        if not task or not task.documents:
            return None
        doc = task.documents[0]
        raw_data = doc.get_raw_data() or {}
        return {
            "id": doc.id,
            "task_id": doc.task_id,
            "owner_name": doc.owner_name,
            "father_name": doc.father_name,
            "village": doc.village,
            "district": doc.district,
            "khata": doc.khata,
            "khasra": doc.khasra,
            "survey_no": doc.survey_no,
            "area": doc.area,
            "reference_number": doc.reference_number,
            "utility_type": raw_data.get("utility_type", "LAND"),
            "consumer_id": raw_data.get("consumer_id"),
            "installation_no": raw_data.get("installation_no"),
            "bill_amount": raw_data.get("bill_amount"),
            "bill_month": raw_data.get("bill_month"),
            "district_code": raw_data.get("district_code"),
            "tehsil_code": raw_data.get("tehsil_code"),
            "village_code": raw_data.get("village_code"),
            "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }

    def close(self):
        self.repository.close()
        self.log_repository.close()
