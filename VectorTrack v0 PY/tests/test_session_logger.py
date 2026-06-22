"""
Tests for the session logger module.
"""

import pytest
import os
import json
from datetime import datetime, timedelta
import sqlite3
from vectortrack.session_logger import SessionLogger, TimeSession

@pytest.fixture
def session_logger(tmp_path):
    """Create a session logger with temporary database."""
    db_path = tmp_path / "test_sessions.db"
    return SessionLogger(str(db_path))

@pytest.fixture
def sample_session():
    """Create a sample time session."""
    return TimeSession(
        project_id="TEST001",
        file_path="test.vwx",
        start_time=datetime.now(),
        hourly_rate=75.0
    )

def test_time_session_creation():
    """Test TimeSession creation and properties."""
    now = datetime.now()
    session = TimeSession(
        project_id="TEST001",
        file_path="test.vwx",
        start_time=now,
        hourly_rate=75.0
    )
    
    assert session.project_id == "TEST001"
    assert session.file_path == "test.vwx"
    assert session.start_time == now
    assert session.end_time is None
    assert session.active_duration == timedelta()
    assert session.hourly_rate == 75.0
    assert session.billable_amount == 0.0

def test_time_session_billable_amount():
    """Test billable amount calculation."""
    session = TimeSession(
        project_id="TEST001",
        file_path="test.vwx",
        start_time=datetime.now(),
        hourly_rate=75.0
    )
    
    # Add 30 minutes of activity
    session.active_duration = timedelta(minutes=30)
    assert session.billable_amount == 37.50  # 75.0 * 0.5

def test_time_session_serialization():
    """Test TimeSession serialization."""
    now = datetime.now()
    session = TimeSession(
        project_id="TEST001",
        file_path="test.vwx",
        start_time=now,
        end_time=now + timedelta(hours=1),
        active_duration=timedelta(minutes=45),
        hourly_rate=75.0
    )
    
    # Test to_dict
    data = session.to_dict()
    assert data['project_id'] == "TEST001"
    assert data['file_path'] == "test.vwx"
    assert data['start_time'] == now.isoformat()
    assert data['end_time'] == (now + timedelta(hours=1)).isoformat()
    assert data['active_duration'] == 45 * 60  # 45 minutes in seconds
    assert data['hourly_rate'] == 75.0
    
    # Test from_dict
    restored = TimeSession.from_dict(data)
    assert restored.project_id == session.project_id
    assert restored.file_path == session.file_path
    assert restored.start_time == session.start_time
    assert restored.end_time == session.end_time
    assert restored.active_duration == session.active_duration
    assert restored.hourly_rate == session.hourly_rate

def test_session_logger_initialization(session_logger, tmp_path):
    """Test SessionLogger initialization."""
    assert os.path.exists(session_logger.db_path)
    
    # Verify table creation
    with sqlite3.connect(session_logger.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert ('sessions',) in tables

def test_start_session(session_logger):
    """Test starting a new session."""
    session = session_logger.start_session(
        project_id="TEST001",
        file_path="test.vwx",
        hourly_rate=75.0
    )
    
    assert session.project_id == "TEST001"
    assert session.file_path == "test.vwx"
    assert session.hourly_rate == 75.0
    assert session.end_time is None
    assert isinstance(session.start_time, datetime)

def test_end_session(session_logger, sample_session):
    """Test ending a session."""
    session_logger.end_session(sample_session)
    
    assert sample_session.end_time is not None
    
    # Verify session was saved to database
    with sqlite3.connect(session_logger.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE project_id=?",
                      (sample_session.project_id,))
        row = cursor.fetchone()
        assert row is not None

def test_update_session_duration(sample_session):
    """Test updating session duration."""
    initial_duration = sample_session.active_duration
    additional_time = timedelta(minutes=15)
    
    SessionLogger().update_session_duration(sample_session, additional_time)
    assert sample_session.active_duration == initial_duration + additional_time

def test_get_project_sessions(session_logger, sample_session):
    """Test retrieving project sessions."""
    # Add a test session
    session_logger.end_session(sample_session)
    
    # Retrieve sessions
    sessions = session_logger.get_project_sessions(sample_session.project_id)
    assert len(sessions) == 1
    assert sessions[0].project_id == sample_session.project_id
    
    # Test date filtering
    future_date = datetime.now() + timedelta(days=1)
    sessions = session_logger.get_project_sessions(
        sample_session.project_id,
        start_date=future_date
    )
    assert len(sessions) == 0

def test_generate_report(session_logger, sample_session, tmp_path):
    """Test report generation."""
    # Add some activity time
    sample_session.active_duration = timedelta(hours=2)
    session_logger.end_session(sample_session)
    
    # Generate report
    report_path = tmp_path / "report.json"
    session_logger.generate_report(
        project_id=sample_session.project_id,
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now() + timedelta(days=1),
        output_path=str(report_path)
    )
    
    # Verify report contents
    assert os.path.exists(report_path)
    with open(report_path) as f:
        report_data = json.load(f)
        
    assert report_data['project_id'] == sample_session.project_id
    assert len(report_data['sessions']) == 1
    assert report_data['summary']['total_hours'] == 2.0
    assert report_data['summary']['total_billable'] == 150.0  # 2 hours * $75 