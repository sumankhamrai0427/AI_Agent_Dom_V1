import datetime
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    objective = Column(Text, nullable=False)
    status = Column(String(50), default='PENDING') # PENDING, PLANNING, RUNNING, PAUSED_CAPTCHA, COMPLETED, FAILED
    current_step = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(Text, default='{}') # state, district, khata, khasra, document_path, etc.
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    logs = relationship("AgentLog", back_populates="task", cascade="all, delete-orphan")
    memories = relationship("BrowserMemory", back_populates="task", cascade="all, delete-orphan")
    documents = relationship("DocumentRecord", back_populates="task", cascade="all, delete-orphan")
    gis_records = relationship("GISRecord", back_populates="task", cascade="all, delete-orphan")
    verifications = relationship("VerificationResult", back_populates="task", cascade="all, delete-orphan")

    def get_metadata(self):
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    def set_metadata(self, data):
        self.metadata_json = json.dumps(data)


class AgentLog(Base):
    __tablename__ = 'agent_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    agent_name = Column(String(100), nullable=False)
    step_name = Column(String(255), nullable=True)
    action = Column(String(100), nullable=True)
    url = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    screenshot_path = Column(String(500), nullable=True)
    execution_time_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    status = Column(String(50), default='SUCCESS') # SUCCESS, FAILURE, RETRYING
    
    task = relationship("Task", back_populates="logs")


class BrowserMemory(Base):
    __tablename__ = 'browser_memories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    task = relationship("Task", back_populates="memories")


class DocumentRecord(Base):
    __tablename__ = 'document_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    owner_name = Column(String(255), nullable=True)
    father_name = Column(String(255), nullable=True)
    village = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    khata = Column(String(255), nullable=True)
    khasra = Column(String(255), nullable=True)
    survey_no = Column(String(255), nullable=True)
    area = Column(String(255), nullable=True)
    reference_number = Column(String(255), nullable=True)
    raw_json = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    task = relationship("Task", back_populates="documents")

    def get_raw_data(self):
        try:
            return json.loads(self.raw_json)
        except Exception:
            return {}


class GISRecord(Base):
    __tablename__ = 'gis_records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    boundary_geojson = Column(Text, nullable=True)
    boundary_kml = Column(Text, nullable=True)
    adjacent_plots_json = Column(Text, default='[]')
    coordinate_system = Column(String(100), default='EPSG:4326')
    map_html_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    task = relationship("Task", back_populates="gis_records")


class VerificationResult(Base):
    __tablename__ = 'verification_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    is_valid = Column(Boolean, default=True)
    conflicts = Column(Text, nullable=True) # JSON list or details of mismatches
    normalized_data_json = Column(Text, default='{}')
    checked_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    task = relationship("Task", back_populates="verifications")


# DB Helper setup
DB_PATH = 'sqlite:///agent_database.db'
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
