"""
Minimal, maintainable persistence service using standard library sqlite3.

LIMITATIONS & SECURITY ARCHITECTURE:
- This solution uses file-based SQLite (resumeiq.db) for single-user and local workspace persistence.
- As authentication does not exist in this application, sessions are namespaced by a client session_id.
- THIS DOES NOT PROVIDE PRIVATE MULTI-USER ACCESS CONTROL OR CRYPTOGRAPHIC TENANT ISOLATION.
- Do not deploy this in multi-tenant environments without integrating user authentication and authorization guards.
"""

import sqlite3
import json
import time
import uuid
import os
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "resumeiq.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                ats_score INTEGER NOT NULL,
                role_target TEXT,
                filename TEXT,
                summary TEXT,
                full_response_json TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS practice_attempts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                target_skill TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                question TEXT NOT NULL,
                user_answer TEXT NOT NULL,
                feedback TEXT NOT NULL,
                score INTEGER NOT NULL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON analysis_history(session_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_practice_session ON practice_attempts(session_id);")


# Initialize tables on load
init_db()


def save_analysis(
    session_id: str,
    ats_score: int,
    role_target: str,
    filename: str,
    summary: str,
    response_data: Dict[str, Any],
) -> str:
    analysis_id = str(uuid.uuid4())
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_history (id, session_id, created_at, ats_score, role_target, filename, summary, full_response_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                session_id,
                time.time(),
                ats_score,
                role_target,
                filename,
                summary,
                json.dumps(response_data),
            ),
        )
    return analysis_id


def list_analyses(session_id: str = "default", limit: int = 20) -> List[Dict[str, Any]]:
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, session_id, created_at, ats_score, role_target, filename, summary
            FROM analysis_history
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_analysis_by_id(analysis_id: str) -> Optional[Dict[str, Any]]:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM analysis_history WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["response"] = json.loads(data.pop("full_response_json"))
        return data


def save_practice_attempt(
    session_id: str,
    target_skill: str,
    difficulty: str,
    question: str,
    user_answer: str,
    feedback: str,
    score: int,
) -> str:
    attempt_id = str(uuid.uuid4())
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO practice_attempts (id, session_id, created_at, target_skill, difficulty, question, user_answer, feedback, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                session_id,
                time.time(),
                target_skill.strip(),
                difficulty,
                question,
                user_answer,
                feedback,
                score,
            ),
        )
    return attempt_id


def get_skill_progress(session_id: str = "default") -> List[Dict[str, Any]]:
    """Calculates aggregate progress and average score per skill for adaptive questions."""
    with _get_connection() as conn:
        rows = conn.execute(
            """
            SELECT 
                target_skill,
                COUNT(*) as attempts_count,
                AVG(score) as avg_score,
                difficulty
            FROM practice_attempts
            WHERE session_id = ?
            GROUP BY target_skill
            ORDER BY avg_score ASC
            """,
            (session_id,),
        ).fetchall()

        results = []
        for r in rows:
            avg_score = round(float(r["avg_score"]), 1)
            if avg_score >= 85:
                status = "mastered"
                curr_diff = "hard"
            elif avg_score >= 65:
                status = "proficient"
                curr_diff = "medium"
            else:
                status = "needs_practice"
                curr_diff = "easy"

            results.append({
                "skill": r["target_skill"],
                "attempts_count": r["attempts_count"],
                "average_score": avg_score,
                "current_difficulty": curr_diff,
                "mastery_status": status,
            })
        return results


def get_adaptive_difficulty_for_skill(session_id: str, skill_name: str, requested_diff: str = "medium") -> str:
    """Adapts difficulty based on recorded candidate performance on this skill."""
    with _get_connection() as conn:
        row = conn.execute(
            """
            SELECT AVG(score) as avg_score, COUNT(*) as cnt
            FROM practice_attempts
            WHERE session_id = ? AND LOWER(target_skill) = LOWER(?)
            """,
            (session_id, skill_name.strip()),
        ).fetchone()

        if not row or row["cnt"] == 0:
            return requested_diff

        avg_score = float(row["avg_score"] or 70.0)
        # Adapt: If struggling (< 60), drop difficulty; if excelling (> 85), raise difficulty
        if avg_score < 60:
            return "easy"
        elif avg_score > 85:
            return "hard"
        return "medium"
