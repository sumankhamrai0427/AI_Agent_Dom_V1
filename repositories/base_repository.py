from models.models import SessionLocal

class BaseRepository:
    def __init__(self, session=None):
        self.session = session or SessionLocal()

    def add(self, entity):
        self.session.add(entity)
        self.commit()
        return entity

    def commit(self):
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def delete(self, entity):
        self.session.delete(entity)
        self.commit()

    def close(self):
        self.session.close()
