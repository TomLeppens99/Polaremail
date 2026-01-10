"""
SQLAlchemy database models for Polar fitness data storage.
Designed to store webhook payloads and API responses for weekly report generation.
"""

from datetime import datetime, date
from typing import Optional
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Date,
    Text, Boolean, JSON, ForeignKey, Index, event
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import StaticPool

from .config import Config

Base = declarative_base()


class Exercise(Base):
    """Stores exercise/training session data from Polar."""

    __tablename__ = 'exercises'

    id = Column(Integer, primary_key=True, autoincrement=True)
    polar_exercise_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Basic exercise info
    sport = Column(String(100))  # e.g., "RUNNING", "CYCLING", "SWIMMING"
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)  # Duration in seconds for easy calculations
    duration_iso = Column(String(50))  # Original ISO-8601 format (PT1H23M45S)

    # Distance and speed
    distance_meters = Column(Float)  # Always stored in meters
    average_speed_kmh = Column(Float)
    max_speed_kmh = Column(Float)

    # Heart rate data
    average_heart_rate = Column(Integer)
    max_heart_rate = Column(Integer)

    # Calories
    calories = Column(Integer)

    # Training load
    training_load_cardio = Column(Float)
    training_load_muscle = Column(Float)
    training_load_perceived = Column(Float)

    # Heart rate zones (stored as JSON: {"zone1": seconds, "zone2": seconds, ...})
    heart_rate_zones = Column(JSON)

    # Additional metrics
    ascent_meters = Column(Float)
    descent_meters = Column(Float)
    average_cadence = Column(Float)
    max_cadence = Column(Float)
    average_power = Column(Float)
    max_power = Column(Float)

    # Running specific
    running_index = Column(Float)

    # Raw payload for reference
    raw_payload = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(20), default='webhook')  # 'webhook' or 'api'

    __table_args__ = (
        Index('ix_exercises_user_date', 'user_id', 'start_time'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'polar_exercise_id': self.polar_exercise_id,
            'sport': self.sport,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'duration_seconds': self.duration_seconds,
            'distance_km': self.distance_meters / 1000 if self.distance_meters else None,
            'calories': self.calories,
            'average_heart_rate': self.average_heart_rate,
            'max_heart_rate': self.max_heart_rate,
            'training_load_cardio': self.training_load_cardio,
            'training_load_muscle': self.training_load_muscle,
            'heart_rate_zones': self.heart_rate_zones,
        }


class SleepRecord(Base):
    """Stores sleep data from Polar."""

    __tablename__ = 'sleep_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    polar_sleep_id = Column(String(100), unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Sleep timing
    sleep_date = Column(Date, nullable=False, index=True)  # The night of sleep
    sleep_start = Column(DateTime)
    sleep_end = Column(DateTime)
    duration_seconds = Column(Integer)

    # Sleep stages (in seconds)
    light_sleep_seconds = Column(Integer)
    deep_sleep_seconds = Column(Integer)
    rem_sleep_seconds = Column(Integer)
    wake_seconds = Column(Integer)  # Time awake during sleep period

    # Sleep quality metrics
    sleep_score = Column(Float)  # 0-100
    sleep_continuity = Column(Float)  # 0-5 scale
    sleep_cycles = Column(Integer)

    # Heart rate during sleep
    average_heart_rate = Column(Integer)
    min_heart_rate = Column(Integer)

    # Breathing
    average_breathing_rate = Column(Float)

    # Raw payload
    raw_payload = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(20), default='webhook')

    __table_args__ = (
        Index('ix_sleep_user_date', 'user_id', 'sleep_date'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'sleep_date': self.sleep_date.isoformat() if self.sleep_date else None,
            'duration_hours': self.duration_seconds / 3600 if self.duration_seconds else None,
            'sleep_score': self.sleep_score,
            'light_sleep_hours': self.light_sleep_seconds / 3600 if self.light_sleep_seconds else None,
            'deep_sleep_hours': self.deep_sleep_seconds / 3600 if self.deep_sleep_seconds else None,
            'rem_sleep_hours': self.rem_sleep_seconds / 3600 if self.rem_sleep_seconds else None,
        }


class NightlyRecharge(Base):
    """Stores Nightly Recharge (recovery/readiness) data."""

    __tablename__ = 'nightly_recharge'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Date of the recharge measurement
    recharge_date = Column(Date, nullable=False, index=True)

    # Nightly Recharge status (1=Very Poor to 5=Very Good)
    nightly_recharge_status = Column(Integer)

    # ANS (Autonomic Nervous System) Charge
    ans_charge = Column(Float)  # -10 to +10 scale

    # Heart Rate Variability
    hrv_avg = Column(Float)  # Average HRV in ms
    hrv_rmssd = Column(Float)  # RMSSD value

    # Breathing rate during sleep
    breathing_rate_avg = Column(Float)

    # Beat-to-beat intervals
    beat_to_beat_avg = Column(Float)

    # Heart rate during sleep
    heart_rate_avg = Column(Integer)

    # Raw payload
    raw_payload = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(20), default='api')

    __table_args__ = (
        Index('ix_recharge_user_date', 'user_id', 'recharge_date', unique=True),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'recharge_date': self.recharge_date.isoformat() if self.recharge_date else None,
            'nightly_recharge_status': self.nightly_recharge_status,
            'ans_charge': self.ans_charge,
            'hrv_avg': self.hrv_avg,
        }


class ActivitySummary(Base):
    """Stores daily activity summary data."""

    __tablename__ = 'activity_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)

    # Activity date
    activity_date = Column(Date, nullable=False, index=True)

    # Daily activity metrics
    active_calories = Column(Integer)
    total_calories = Column(Integer)
    steps = Column(Integer)
    active_time_seconds = Column(Integer)

    # Activity goal progress (percentage)
    activity_goal_percent = Column(Float)

    # Raw payload
    raw_payload = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(20), default='webhook')

    __table_args__ = (
        Index('ix_activity_user_date', 'user_id', 'activity_date', unique=True),
    )


class WebhookEvent(Base):
    """Stores raw webhook events for debugging and audit purposes."""

    __tablename__ = 'webhook_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)  # EXERCISE, SLEEP, ACTIVITY_SUMMARY
    event_id = Column(String(100), index=True)
    user_id = Column(String(100), index=True)

    # Raw webhook payload
    payload = Column(JSON, nullable=False)

    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    error_message = Column(Text)

    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index('ix_webhook_type_date', 'event_type', 'received_at'),
    )


class User(Base):
    """Stores Polar user information and tokens."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    polar_user_id = Column(String(100), unique=True, nullable=False, index=True)

    # User info from Polar
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    birthdate = Column(Date)
    gender = Column(String(20))
    weight = Column(Float)  # kg
    height = Column(Float)  # cm

    # OAuth tokens
    access_token = Column(String(500))
    token_type = Column(String(50), default='bearer')

    # Registration status
    registered_at = Column(DateTime)
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database engine and session management
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        # SQLite-specific configuration
        if Config.DATABASE_URL.startswith('sqlite'):
            _engine = create_engine(
                Config.DATABASE_URL,
                connect_args={'check_same_thread': False},
                poolclass=StaticPool,
                echo=Config.FLASK_DEBUG
            )
        else:
            _engine = create_engine(Config.DATABASE_URL, echo=Config.FLASK_DEBUG)
    return _engine


def get_session():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Initialize the database (create all tables)."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def drop_db():
    """Drop all tables (use with caution!)."""
    engine = get_engine()
    Base.metadata.drop_all(engine)


# Utility functions for common queries
def get_exercises_in_range(session, user_id: str, start_date: date, end_date: date) -> list:
    """Get all exercises within a date range."""
    from sqlalchemy import and_
    return session.query(Exercise).filter(
        and_(
            Exercise.user_id == user_id,
            Exercise.start_time >= datetime.combine(start_date, datetime.min.time()),
            Exercise.start_time < datetime.combine(end_date, datetime.max.time())
        )
    ).order_by(Exercise.start_time).all()


def get_sleep_in_range(session, user_id: str, start_date: date, end_date: date) -> list:
    """Get all sleep records within a date range."""
    from sqlalchemy import and_
    return session.query(SleepRecord).filter(
        and_(
            SleepRecord.user_id == user_id,
            SleepRecord.sleep_date >= start_date,
            SleepRecord.sleep_date <= end_date
        )
    ).order_by(SleepRecord.sleep_date).all()


def get_recharge_in_range(session, user_id: str, start_date: date, end_date: date) -> list:
    """Get all nightly recharge records within a date range."""
    from sqlalchemy import and_
    return session.query(NightlyRecharge).filter(
        and_(
            NightlyRecharge.user_id == user_id,
            NightlyRecharge.recharge_date >= start_date,
            NightlyRecharge.recharge_date <= end_date
        )
    ).order_by(NightlyRecharge.recharge_date).all()
