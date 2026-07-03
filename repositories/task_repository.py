import json
from repositories.base_repository import BaseRepository
from models.models import Task, BrowserMemory, DocumentRecord, GISRecord, VerificationResult

class TaskRepository(BaseRepository):
    def create_task(self, objective, metadata=None):
        task = Task(objective=objective)
        if metadata:
            task.set_metadata(metadata)
        return self.add(task)

    def get_task(self, task_id):
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
        return self.session.query(Task).filter(Task.id == task_id).first()

    def get_all_tasks(self):
        return self.session.query(Task).order_by(Task.created_at.desc()).all()

    def update_status(self, task_id, status=None, error_message=None, current_step=None):
        task = self.get_task(task_id)
        if task:
            if status is not None:
                task.status = status
            if error_message is not None:
                task.error_message = error_message
            if current_step is not None:
                task.current_step = current_step
            self.commit()
        return task

    def save_document_record(self, task_id, data_dict):
        record = DocumentRecord(
            task_id=task_id,
            owner_name=data_dict.get('owner_name'),
            father_name=data_dict.get('father_name'),
            village=data_dict.get('village'),
            district=data_dict.get('district'),
            khata=data_dict.get('khata'),
            khasra=data_dict.get('khasra'),
            survey_no=data_dict.get('survey_no'),
            area=data_dict.get('area'),
            reference_number=data_dict.get('reference_number'),
            raw_json=json.dumps(data_dict)
        )
        return self.add(record)

    def save_gis_record(self, task_id, geojson, kml, adjacent_plots, coordinate_system, map_html_path):
        record = GISRecord(
            task_id=task_id,
            boundary_geojson=geojson if isinstance(geojson, str) else json.dumps(geojson),
            boundary_kml=kml,
            adjacent_plots_json=adjacent_plots if isinstance(adjacent_plots, str) else json.dumps(adjacent_plots),
            coordinate_system=coordinate_system,
            map_html_path=map_html_path
        )
        return self.add(record)

    def save_verification_result(self, task_id, is_valid, conflicts, normalized_data):
        record = VerificationResult(
            task_id=task_id,
            is_valid=is_valid,
            conflicts=conflicts if isinstance(conflicts, str) else json.dumps(conflicts),
            normalized_data_json=normalized_data if isinstance(normalized_data, str) else json.dumps(normalized_data)
        )
        return self.add(record)

    def get_task_memories(self, task_id):
        memories = self.session.query(BrowserMemory).filter(BrowserMemory.task_id == task_id).all()
        return {m.key: m.value for m in memories}

    def set_task_memory(self, task_id, key, value):
        memory = self.session.query(BrowserMemory).filter(
            BrowserMemory.task_id == task_id,
            BrowserMemory.key == key
        ).first()
        if memory:
            memory.value = str(value)
            self.commit()
        else:
            memory = BrowserMemory(task_id=task_id, key=key, value=str(value))
            self.add(memory)
        return memory

    def get_task_memory(self, task_id, key):
        memory = self.session.query(BrowserMemory).filter(
            BrowserMemory.task_id == task_id,
            BrowserMemory.key == key
        ).first()
        return memory.value if memory else None
