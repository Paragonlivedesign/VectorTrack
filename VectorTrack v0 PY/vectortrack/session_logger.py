"""
Session logging module for tracking time and generating reports.
"""

import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List
from pathlib import Path
import sqlite3
from loguru import logger

@dataclass
class TimeSession:
    project_id: str
    file_path: str
    start_time: datetime
    end_time: Optional[datetime] = None
    active_duration: timedelta = timedelta()
    hourly_rate: float = 0.0
    
    @property
    def billable_amount(self) -> float:
        """Calculate billable amount based on active duration and hourly rate."""
        hours = self.active_duration.total_seconds() / 3600
        return round(hours * self.hourly_rate, 2)
        
    def to_dict(self) -> dict:
        """Convert session to dictionary for storage."""
        data = asdict(self)
        data['start_time'] = data['start_time'].isoformat()
        data['end_time'] = data['end_time'].isoformat() if data['end_time'] else None
        data['active_duration'] = data['active_duration'].total_seconds()
        return data
        
    @classmethod
    def from_dict(cls, data: dict) -> 'TimeSession':
        """Create session from dictionary."""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        if data['end_time']:
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        data['active_duration'] = timedelta(seconds=data['active_duration'])
        return cls(**data)

class SessionLogger:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    active_duration REAL NOT NULL,
                    hourly_rate REAL NOT NULL
                )
            """)
            
    def start_session(self, project_id: str, file_path: str, hourly_rate: float) -> TimeSession:
        """Start a new time tracking session."""
        session = TimeSession(
            project_id=project_id,
            file_path=file_path,
            start_time=datetime.now(),
            hourly_rate=hourly_rate
        )
        logger.info(f"[SESSION] Started new session - Project: {project_id}, File: {file_path}, Rate: ${hourly_rate:.2f}/hr")
        return session
        
    def end_session(self, session: TimeSession):
        """End a time tracking session."""
        if session:
            session.end_time = datetime.now()
            duration = str(session.active_duration).split('.')[0]  # Remove microseconds
            logger.info(f"[SESSION] Ended session - Project: {session.project_id}, Duration: {duration}, Amount: ${session.billable_amount:.2f}")

    def update_session_duration(self, session: TimeSession, duration: timedelta):
        """Update the active duration of a session."""
        if session:
            session.active_duration += duration
            # Only log significant time updates (e.g., every minute)
            if duration.total_seconds() >= 60:
                total_duration = str(session.active_duration).split('.')[0]  # Remove microseconds
                logger.info(f"[SESSION] Updated duration - Project: {session.project_id}, Total: {total_duration}, Amount: ${session.billable_amount:.2f}")

    def _save_session(self, session: TimeSession):
        """Save session to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions 
                (project_id, file_path, start_time, end_time, active_duration, hourly_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.project_id,
                session.file_path,
                session.start_time.isoformat(),
                session.end_time.isoformat() if session.end_time else None,
                session.active_duration.total_seconds(),
                session.hourly_rate
            ))
            
    def get_project_sessions(self, project_id: str, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[TimeSession]:
        """Retrieve sessions for a specific project within date range."""
        query = "SELECT * FROM sessions WHERE project_id = ?"
        params = [project_id]
        
        if start_date:
            query += " AND start_time >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND start_time <= ?"
            params.append(end_date.isoformat())
            
        sessions = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute(query, params):
                session_dict = dict(row)
                # Remove the id field as it's not part of TimeSession
                session_dict.pop('id', None)
                sessions.append(TimeSession.from_dict(session_dict))
        return sessions
        
    def generate_report(self, project_id: str, start_date: datetime,
                       end_date: datetime, output_path: str):
        """Generate a detailed report for a project."""
        sessions = self.get_project_sessions(project_id, start_date, end_date)
        
        total_duration = timedelta()
        total_billable = 0.0
        
        report_data = {
            'project_id': project_id,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'sessions': [],
            'summary': {}
        }
        
        for session in sessions:
            total_duration += session.active_duration
            total_billable += session.billable_amount
            report_data['sessions'].append(session.to_dict())
            
        report_data['summary'] = {
            'total_hours': round(total_duration.total_seconds() / 3600, 2),
            'total_billable': round(total_billable, 2)
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"Generated report for project {project_id} at {output_path}")

    def clear_all_sessions(self):
        """Clear all session data."""
        logger.info("[SESSION] All session data cleared") 