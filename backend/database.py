# =============================================================================
# database.py — SQLite Persistence for Metrics
# =============================================================================
# Stores pipeline run history and aggregated metrics in a local SQLite
# database. This allows the Streamlit dashboard to show:
#   - Total requests processed
#   - Success rate
#   - Average response time
#   - Validation failure count
#   - Repair count
#
# Database file: data/app_generator.db (created automatically)
#
# Tables:
#   - pipeline_runs: One row per pipeline execution
# =============================================================================

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional

from backend.schemas import PipelineResult

logger = logging.getLogger(__name__)

# Database file path — flexible for local dev and Vercel deployment
# On Vercel, the filesystem is read-only except /tmp, so we use /tmp for the DB
def _get_db_path() -> str:
    """Determine the database path based on the environment."""
    if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
        # Vercel serverless: use /tmp (only writable directory)
        db_dir = "/tmp/data"
    elif os.environ.get("DB_DIR"):
        # Custom path via environment variable
        db_dir = os.environ["DB_DIR"]
    else:
        # Local development: use data/ directory relative to project root
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    return db_dir

DB_DIR = _get_db_path()
DB_PATH = os.path.join(DB_DIR, "app_generator.db")


def _get_connection() -> sqlite3.Connection:
    """
    Get a connection to the SQLite database.
    Creates the database file and tables if they don't exist.
    """
    # Ensure the data directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    
    # Create tables if they don't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            prompt TEXT NOT NULL,
            success INTEGER NOT NULL,
            processing_time REAL NOT NULL,
            validation_passed INTEGER DEFAULT 0,
            repair_count INTEGER DEFAULT 0,
            app_ready INTEGER DEFAULT 0,
            error_message TEXT,
            result_json TEXT
        )
    """)
    conn.commit()
    
    return conn


def save_pipeline_run(result: PipelineResult) -> None:
    """
    Save a pipeline run result to the database.
    
    Extracts key metrics from the PipelineResult and stores them
    alongside the full result JSON for later retrieval.
    
    Args:
        result: The PipelineResult from a completed pipeline run
    """
    try:
        conn = _get_connection()
        
        # Extract metrics from the result
        validation_passed = 0
        if result.validation_report:
            validation_passed = 1 if result.validation_report.is_valid else 0
        
        repair_count = 0
        if result.repair_report:
            repair_count = result.repair_report.repair_count
        
        app_ready = 0
        if result.execution_result:
            app_ready = 1 if result.execution_result.app_ready else 0
        
        # Serialize the full result to JSON for storage
        result_json = result.model_dump_json()
        
        conn.execute(
            """
            INSERT INTO pipeline_runs 
            (timestamp, prompt, success, processing_time, validation_passed,
             repair_count, app_ready, error_message, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(),
                result.prompt,
                1 if result.success else 0,
                result.processing_time_seconds,
                validation_passed,
                repair_count,
                app_ready,
                result.error_message,
                result_json,
            ),
        )
        conn.commit()
        conn.close()
        
        logger.info("Pipeline run saved to database")
        
    except Exception as e:
        logger.error(f"Failed to save pipeline run: {str(e)}")


def get_metrics() -> dict:
    """
    Get aggregated metrics from all pipeline runs.
    
    Returns:
        dict with keys:
            - total_requests: Total number of pipeline runs
            - success_count: Number of successful runs
            - success_rate: Percentage of successful runs (0-100)
            - avg_response_time: Average processing time in seconds
            - validation_failures: Number of runs where validation failed
            - total_repairs: Total number of repairs across all runs
            - app_ready_count: Number of runs that produced app_ready=True
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        # Get total requests
        cursor.execute("SELECT COUNT(*) FROM pipeline_runs")
        total_requests = cursor.fetchone()[0]
        
        if total_requests == 0:
            conn.close()
            return {
                "total_requests": 0,
                "success_count": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "validation_failures": 0,
                "total_repairs": 0,
                "app_ready_count": 0,
            }
        
        # Get success count
        cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE success = 1")
        success_count = cursor.fetchone()[0]
        
        # Get average response time
        cursor.execute("SELECT AVG(processing_time) FROM pipeline_runs")
        avg_response_time = cursor.fetchone()[0] or 0.0
        
        # Get validation failures
        cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE validation_passed = 0")
        validation_failures = cursor.fetchone()[0]
        
        # Get total repairs
        cursor.execute("SELECT SUM(repair_count) FROM pipeline_runs")
        total_repairs = cursor.fetchone()[0] or 0
        
        # Get app ready count
        cursor.execute("SELECT COUNT(*) FROM pipeline_runs WHERE app_ready = 1")
        app_ready_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_requests": total_requests,
            "success_count": success_count,
            "success_rate": round((success_count / total_requests) * 100, 1),
            "avg_response_time": round(avg_response_time, 2),
            "validation_failures": validation_failures,
            "total_repairs": total_repairs,
            "app_ready_count": app_ready_count,
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        return {
            "total_requests": 0,
            "success_count": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "validation_failures": 0,
            "total_repairs": 0,
            "app_ready_count": 0,
        }


def get_run_history(limit: int = 20) -> list[dict]:
    """
    Get the most recent pipeline runs.
    
    Args:
        limit: Maximum number of runs to return (default: 20)
        
    Returns:
        List of dicts with run summary information
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, timestamp, prompt, success, processing_time,
                   validation_passed, repair_count, app_ready, error_message
            FROM pipeline_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        
        runs = []
        for row in cursor.fetchall():
            runs.append({
                "id": row[0],
                "timestamp": row[1],
                "prompt": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
                "success": bool(row[3]),
                "processing_time": row[4],
                "validation_passed": bool(row[5]),
                "repair_count": row[6],
                "app_ready": bool(row[7]),
                "error_message": row[8],
            })
        
        conn.close()
        return runs
        
    except Exception as e:
        logger.error(f"Failed to get run history: {str(e)}")
        return []
