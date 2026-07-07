import os
from flask import Flask
from models.models import init_db
from controllers.task_controller import TaskController
from utils.logger import logger
from utils.socket_instance import socketio

app = Flask(__name__, static_folder="static", template_folder="templates")
controller = TaskController()

# Initialize SocketIO with Flask app/////
socketio.init_app(app)

@socketio.on('connect')
def handle_connect():
    logger.info("Client connected to SocketIO server.")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info("Client disconnected from SocketIO server.")

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

@app.route("/api/storage/download/reports/<path:filename>")
def download_report(filename):
    return controller.download_report(filename)

@app.route("/api/storage/uploads/<path:filename>")
def serve_upload(filename):
    return controller.serve_upload(filename)

@app.route("/api/storage/historical_bills/<path:filename>")
def serve_historical_bill(filename):
    return controller.serve_historical_bill(filename)

# Create local storage folders on start
os.makedirs("storage/screenshots", exist_ok=True)
os.makedirs("storage/reports", exist_ok=True)
os.makedirs("storage/uploads", exist_ok=True)

if __name__ == "__main__":
    logger.info("Initializing database...")
    init_db()
    
    # Auto-cleanup stale RUNNING/PENDING tasks on server startup
    try:
        from models.models import SessionLocal, Task
        db = SessionLocal()
        stuck_tasks = db.query(Task).filter(Task.status.in_(["RUNNING", "PAUSED_CAPTCHA", "PENDING"])).all()
        for t in stuck_tasks:
            logger.info(f"Cleaning up stale task #{t.id} from previous session.")
            t.status = "FAILED"
            t.error_message = "Server restarted during execution."
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Failed to clean up stale tasks on startup: {e}")

    logger.info("Starting Flask SocketIO server on http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)

