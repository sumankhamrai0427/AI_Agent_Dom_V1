from utils.logger import logger

class MemoryManager:
    def __init__(self, task_id, repository=None):
        self.task_id = task_id
        self.repository = repository
        self.visited_urls = set()
        self.downloaded_files = []
        self.variables = {}
        self.action_history = []
        
        # Load existing memory from repo if available
        if self.repository:
            try:
                db_memories = self.repository.get_task_memories(self.task_id)
                for key, val in db_memories.items():
                    if key == "visited_urls":
                        self.visited_urls = set(val.split(",")) if val else set()
                    elif key == "downloaded_files":
                        self.downloaded_files = val.split(",") if val else []
                    elif key == "action_history":
                        self.action_history = val.split(" -> ") if val else []
                    else:
                        self.variables[key] = val
                logger.info(f"Loaded memory for Task #{self.task_id}: {self.variables}")
            except Exception as e:
                logger.error(f"Error loading task memories: {e}")

    def update_variable(self, key, value):
        self.variables[key] = str(value)
        if self.repository:
            try:
                self.repository.set_task_memory(self.task_id, key, str(value))
            except Exception as e:
                logger.error(f"Failed to update variable {key} in DB: {e}")

    def get_variable(self, key, default=None):
        return self.variables.get(key, default)

    def log_url(self, url):
        if url not in self.visited_urls:
            self.visited_urls.add(url)
            if self.repository:
                try:
                    self.repository.set_task_memory(self.task_id, "visited_urls", ",".join(self.visited_urls))
                except Exception as e:
                    logger.error(f"Failed to save visited URL in DB: {e}")

    def log_download(self, filepath):
        if filepath not in self.downloaded_files:
            self.downloaded_files.append(filepath)
            if self.repository:
                try:
                    self.repository.set_task_memory(self.task_id, "downloaded_files", ",".join(self.downloaded_files))
                except Exception as e:
                    logger.error(f"Failed to save download details in DB: {e}")

    def log_action(self, action_desc):
        self.action_history.append(action_desc)
        if self.repository:
            try:
                self.repository.set_task_memory(self.task_id, "action_history", " -> ".join(self.action_history))
            except Exception as e:
                logger.error(f"Failed to log action history in DB: {e}")

    def has_action_been_done(self, action_desc):
        return action_desc in self.action_history

    def get_memory_summary(self):
        """Returns a dict summary of memory for LLM prompts."""
        return {
            "visited_pages": list(self.visited_urls),
            "downloaded_files": self.downloaded_files,
            "variables": self.variables,
            "recent_actions": self.action_history[-5:]
        }
