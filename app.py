import os
from flask import Flask
from models.models import init_db
from controllers.task_controller import TaskController
from utils.logger import logger

app = Flask(__name__, static_folder="static", template_folder="templates")
controller = TaskController()

@app.route("/")
def index():
    return controller.index()

# --- API Routes ---

@app.route("/api/tasks", methods=["POST"])
def submit_task():
    return controller.submit_task()

@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    return controller.list_tasks()

@app.route("/api/tasks/<int:task_id>", methods=["GET"])
def get_task_status(task_id):
    return controller.get_task_status(task_id)

@app.route("/api/tasks/<int:task_id>/solve-captcha", methods=["POST"])
def resolve_captcha(task_id):
    return controller.resolve_captcha(task_id)

@app.route("/api/tasks/<int:task_id>/document-data", methods=["GET"])
def get_task_document_data(task_id):
    return controller.get_task_document_data(task_id)

# File server routes
@app.route("/api/storage/screenshots/<path:filename>")
def serve_screenshot(filename):
    return controller.serve_screenshot(filename)

@app.route("/api/storage/reports/<path:filename>")
def serve_report(filename):
    return controller.serve_report(filename)

# Create local storage folders on start
os.makedirs("storage/screenshots", exist_ok=True)
os.makedirs("storage/reports", exist_ok=True)
os.makedirs("storage/uploads", exist_ok=True)

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting Flask application server on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
