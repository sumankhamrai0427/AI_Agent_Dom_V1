import os
from repositories.base_repository import BaseRepository
from models.models import AgentLog
from utils.logger import logger

class AgentLogRepository(BaseRepository):
    def log_action(self, task_id, agent_name, step_name, action, url=None, result=None, screenshot_path=None, execution_time_ms=0, error_message=None, retry_count=0, status='SUCCESS'):
        log = AgentLog(
            task_id=task_id,
            agent_name=agent_name,
            step_name=step_name,
            action=action,
            url=url,
            result=result,
            screenshot_path=screenshot_path,
            execution_time_ms=execution_time_ms,
            error_message=error_message,
            retry_count=retry_count,
            status=status
        )
        saved_log = self.add(log)
        
        # Broadcast real-time log update to frontend via SocketIO
        try:
            from utils.socket_instance import socketio
            screenshot_url = None
            if screenshot_path:
                screenshot_url = f"/api/storage/screenshots/{os.path.basename(screenshot_path)}"
                
            socketio.emit("log_added", {
                "task_id": task_id,
                "agent_name": agent_name,
                "step_name": step_name,
                "action": action,
                "url": url,
                "result": result,
                "screenshot_url": screenshot_url,
                "status": status,
                "error_message": error_message
            })
            # Broadcast global task status update event
            socketio.emit("task_updated", {
                "task_id": task_id,
                "status": status
            })
        except Exception as e:
            logger.error(f"Failed to broadcast log event via SocketIO: {e}")
            
        return saved_log

    def get_logs_for_task(self, task_id):
        return self.session.query(AgentLog).filter(AgentLog.task_id == task_id).order_by(AgentLog.timestamp.asc()).all()
