import os
from flask import jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from services.task_service import TaskService
from utils.config import UPLOAD_DIR
from utils.logger import logger

class TaskController:
    def __init__(self):
        self.service = TaskService()

    def submit_task(self):
        try:
            # Parse form fields
            objective = request.form.get("objective")
            state = request.form.get("state", "UP").upper()
            district = request.form.get("district", "").strip()
            village = request.form.get("village", "").strip()
            khata = request.form.get("khata", "").strip()
            owner_name = request.form.get("owner_name", "").strip()
            
            if not objective:
                objective = f"Verify Land Ownership Deed for Khata {khata} in Village {village}, {district}, {state}."

            metadata = {
                "state": state,
                "district": district,
                "village": village,
                "khata": khata,
                "owner_name": owner_name,
                "document_path": None
            }

            # Handle deed file upload (optional)
            if "deed_file" in request.files:
                file = request.files["deed_file"]
                if file and file.filename != "":
                    filename = secure_filename(file.filename)
                    dest_path = os.path.join(UPLOAD_DIR, filename)
                    file.save(dest_path)
                    metadata["document_path"] = dest_path
                    logger.info(f"File uploaded and saved to: {dest_path}")

            task = self.service.create_search_task(objective, metadata)
            
            return jsonify({
                "success": True,
                "message": "Task successfully created and queued.",
                "task_id": task.id,
                "status": task.status
            }), 202

        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def get_task_status(self, task_id):
        try:
            task_details = self.service.get_task_details(int(task_id))
            if not task_details:
                return jsonify({"success": False, "error": "Task not found"}), 404
            return jsonify({"success": True, "task": task_details}), 200
        except Exception as e:
            logger.error(f"Failed to fetch task status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def list_tasks(self):
        try:
            tasks = self.service.get_all_tasks()
            return jsonify({"success": True, "tasks": tasks}), 200
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def resolve_captcha(self, task_id):
        try:
            success = self.service.solve_captcha(int(task_id))
            if not success:
                return jsonify({"success": False, "error": "Failed to resume task. Make sure task is in PAUSED_CAPTCHA state."}), 400
            return jsonify({"success": True, "message": "Resumed task successfully."}), 200
        except Exception as e:
            logger.error(f"Failed to resolve CAPTCHA: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    def get_task_document_data(self, task_id):
        try:
            doc_data = self.service.get_task_document_data(int(task_id))
            if not doc_data:
                return jsonify({"success": False, "error": "Document data not found or not extracted yet for this task."}), 404
            return jsonify({"success": True, "document_data": doc_data}), 200
        except Exception as e:
            logger.error(f"Failed to fetch task document data: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
            
    def index(self):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return send_from_directory(os.path.join(root_path, "templates"), "index.html")

    def serve_screenshot(self, filename):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return send_from_directory(
            os.path.join(root_path, "storage", "screenshots"),
            filename
        )

    def serve_report(self, filename):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return send_from_directory(
            os.path.join(root_path, "storage", "reports"),
            filename
        )
        
    def download_report(self, filename):
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return send_from_directory(
            os.path.join(root_path, "storage", "reports"),
            filename,
            as_attachment=True
        )
            
    def cleanup(self):
        self.service.close()
