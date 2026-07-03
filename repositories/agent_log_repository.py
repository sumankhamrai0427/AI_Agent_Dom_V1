from repositories.base_repository import BaseRepository
from models.models import AgentLog

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
        return self.add(log)

    def get_logs_for_task(self, task_id):
        return self.session.query(AgentLog).filter(AgentLog.task_id == task_id).order_by(AgentLog.timestamp.asc()).all()
