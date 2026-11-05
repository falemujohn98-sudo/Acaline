import json
import os
import secrets
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from random import Random

# Ensure project root (ml/) is on sys.path for cross-package imports
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.ml_models.tests.predict import predict_career

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "database_sqliteDB" / "app.db"
QUESTIONS_PATH = BASE_DIR / "assessment_questions.json"

TEST_CONFIG = [
    {
        "slug": "aptitude",
        "title": "Aptitude Test",
        "category": "aptitude",
        "question_count": 10,
    },
    {
        "slug": "cognitive",
        "title": "Cognitive Test",
        "category": "cognitive",
        "question_count": 10,
    },
    {
        "slug": "psychometric",
        "title": "Psychometric Test",
        "category": "psychometric",
        "question_count": 10,
    },
    {
        "slug": "personality",
        "title": "Personality Test",
        "category": "personality",
        "question_count": 10,
    },
]


def _ensure_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check if we need to migrate/recreate schema (e.g. if 'password' column doesn't exist)
    try:
        conn.execute("SELECT password FROM students LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("DROP TABLE IF EXISTS students")
        conn.execute("DROP TABLE IF EXISTS assessments")
        conn.commit()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            phone TEXT,
            dob TEXT,
            gender TEXT,
            class_level TEXT,
            department TEXT,
            school_name TEXT,
            school_type TEXT,
            state TEXT,
            language TEXT,
            uploaded_results TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def _load_question_bank() -> List[Dict[str, Any]]:
    if QUESTIONS_PATH.exists():
        with QUESTIONS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
    return []


def _seed_question_bank_if_missing() -> List[Dict[str, Any]]:
    return _load_question_bank()


def get_question_bank_stats() -> Dict[str, Any]:
    questions = _load_question_bank()
    per_category = {}
    for category in ["aptitude", "cognitive", "psychometric", "personality"]:
        per_category[category] = sum(1 for q in questions if q.get("category") == category)
    return {
        "total_questions": len(questions),
        "per_category": per_category,
    }


def get_student_attempt_count(student_id: str) -> int:
    conn = _ensure_db()
    row = conn.execute(
        "SELECT COUNT(*) as count FROM assessments WHERE student_id = ?",
        (student_id,),
    ).fetchone()
    conn.close()
    return row["count"] if row else 0


def _normalise_subject_category(value: Any) -> str:
    raw = str(value or "General").strip().lower()
    if "art" in raw:
        return "Arts"
    if "commercial" in raw or "business" in raw:
        return "Commercial"
    if "science" in raw:
        return "Science"
    return "General"


def _shuffle_options_for_question(question: Dict[str, Any], rng: Random) -> List[str]:
    options = list(question.get("options", []))
    if str(question.get("category", "")).lower() in {"aptitude", "cognitive"}:
        rng.shuffle(options)
    return options


def build_assessment_session(student_id: str, shuffle_seed: Optional[str] = None) -> Dict[str, Any]:
    student_row = db_get_student(student_id)
    if not student_row:
        dept = "Science"
    else:
        dept = student_row.get("department", "Science") or "Science"
    
    subj_cat = _normalise_subject_category(dept)

    questions = _load_question_bank()
    attempt_count = get_student_attempt_count(student_id)
    # Use a fresh session salt so each login/session receives a new arrangement.
    # Tests may pass shuffle_seed for deterministic assertions.
    session_seed = shuffle_seed or secrets.token_urlsafe(16)
    rng = Random(f"{student_id}-{attempt_count}-{session_seed}")
    
    tests = []
    for config in TEST_CONFIG:
        department_questions = [
            q for q in questions 
            if str(q.get("category")).lower() == config["category"].lower() and 
            _normalise_subject_category(q.get("subject_category")) == subj_cat
        ]
        general_questions = [
            q for q in questions
            if str(q.get("category")).lower() == config["category"].lower() and
            _normalise_subject_category(q.get("subject_category")) == "General"
        ]
        rng.shuffle(department_questions)
        rng.shuffle(general_questions)
        category_questions = department_questions + general_questions

        if len(category_questions) < config["question_count"]:
            # Fill up with other questions from the same category if department specific count is insufficient
            extra_questions = [
                q for q in questions
                if str(q.get("category")).lower() == config["category"].lower() and q not in category_questions
            ]
            rng.shuffle(extra_questions)
            category_questions.extend(extra_questions)
            
        if category_questions:
            selected = category_questions[: config["question_count"]]
        else:
            selected = []
            
        tests.append(
            {
                "slug": config["slug"],
                "title": config["title"],
                "category": config["category"],
                "question_count": len(selected),
                "questions": [
                    {
                        "id": q["id"],
                        "prompt": q["prompt"],
                        "options": _shuffle_options_for_question(q, rng),
                        "subject_category": q.get("subject_category", "General"),
                        "source": q.get("source", ""),
                    }
                    for q in selected
                ],
            }
        )
    return {
        "student_id": student_id,
        "tests": tests,
        "created_at": str(uuid.uuid4())[:8],
    }


def save_assessment(student_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    conn = _ensure_db()
    assessment_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO assessments (id, student_id, payload) VALUES (?, ?, ?)",
        (assessment_id, student_id, json.dumps(payload)),
    )
    conn.commit()
    conn.close()
    return {"assessment_id": assessment_id, "student_id": student_id}


def get_assessment_history(student_id: str) -> List[Dict[str, Any]]:
    conn = _ensure_db()
    rows = conn.execute(
        "SELECT id, payload, created_at FROM assessments WHERE student_id = ? ORDER BY created_at DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [
        {"id": row["id"], "payload": json.loads(row["payload"]), "created_at": row["created_at"]}
        for row in rows
    ]


# DB Helper operations for Students
def db_create_student(student_data: dict) -> bool:
    conn = _ensure_db()
    try:
        conn.execute(
            """
            INSERT INTO students (id, name, email, password, phone, dob, gender, class_level, department, school_name, school_type, state, language, uploaded_results)
            VALUES (:id, :name, :email, :password, :phone, :dob, :gender, :class_level, :department, :school_name, :school_type, :state, :language, :uploaded_results)
            """,
            student_data
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def db_get_student_by_email(email: str) -> Dict[str, Any]:
    conn = _ensure_db()
    row = conn.execute("SELECT * FROM students WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def db_get_student(student_id: str) -> Dict[str, Any]:
    conn = _ensure_db()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def db_update_student_profile(student_id: str, updates: dict) -> bool:
    conn = _ensure_db()
    fields = []
    values = []
    for k, v in updates.items():
        fields.append(f"{k} = ?")
        values.append(v)
    values.append(student_id)
    
    query = f"UPDATE students SET {', '.join(fields)} WHERE id = ?"
    try:
        conn.execute(query, values)
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# Grading function
def grade_answers(answers: Dict[str, str]) -> Dict[str, float]:
    """
    Grades user answers and calculates:
    - aptitude_score_10 (out of 10)
    - cognitive_score_10 (out of 10)
    - psychometric_avg_5 (1-5 Likert scale average)
    - sentiment_avg_5 (1-5 Likert scale average)
    """
    questions = _load_question_bank()
    q_map = {q["id"]: q for q in questions}
    
    category_scores = {
        "aptitude": {"correct": 0, "total": 0},
        "cognitive": {"correct": 0, "total": 0},
        "psychometric": {"sum": 0, "total": 0},
        "personality": {"sum": 0, "total": 0}
    }
    
    # Value mappings for Likert scales
    psychometric_map = {
        "strongly disagree": 1.0,
        "disagree": 2.0,
        "neutral": 3.0,
        "agree": 4.0,
        "strongly agree": 5.0
    }
    
    personality_map = {
        "never": 1.0,
        "sometimes": 2.0,
        "often": 4.0,
        "always": 5.0
    }
    
    for q_id, user_ans in answers.items():
        if q_id not in q_map:
            continue
        q = q_map[q_id]
        category = q["category"]
        
        if category in ["aptitude", "cognitive"]:
            category_scores[category]["total"] += 1
            if str(user_ans).strip().lower() == str(q["answer"]).strip().lower():
                category_scores[category]["correct"] += 1
        elif category == "psychometric":
            ans_clean = str(user_ans).strip().lower()
            val = psychometric_map.get(ans_clean, 3.0) # default neutral
            category_scores["psychometric"]["sum"] += val
            category_scores["psychometric"]["total"] += 1
        elif category == "personality":
            ans_clean = str(user_ans).strip().lower()
            val = personality_map.get(ans_clean, 3.0) # default neutral
            category_scores["personality"]["sum"] += val
            category_scores["personality"]["total"] += 1
            
    # Calculate averages/scaled scores
    results = {}
    
    # Aptitude (scaled to 10)
    apt_stats = category_scores["aptitude"]
    results["aptitude_score_10"] = float(round((apt_stats["correct"] / apt_stats["total"]) * 10, 1)) if apt_stats["total"] > 0 else 5.0
    
    # Cognitive (scaled to 10)
    cog_stats = category_scores["cognitive"]
    results["cognitive_score_10"] = float(round((cog_stats["correct"] / cog_stats["total"]) * 10, 1)) if cog_stats["total"] > 0 else 5.0
    
    # Psychometric (average out of 5)
    psy_stats = category_scores["psychometric"]
    results["psychometric_avg_5"] = float(round(psy_stats["sum"] / psy_stats["total"], 2)) if psy_stats["total"] > 0 else 3.0
    
    # Personality (average out of 5)
    per_stats = category_scores["personality"]
    results["sentiment_avg_5"] = float(round(per_stats["sum"] / per_stats["total"], 2)) if per_stats["total"] > 0 else 3.0

    # Ensure all keys exist (defensive fix)
    defaults = {
        "aptitude_score_10": 5.0,
        "cognitive_score_10": 5.0,
        "psychometric_avg_5": 3.0,
        "sentiment_avg_5": 3.0
    }
    for k, v in defaults.items():
        if k not in results:
            results[k] = v
    
    return results


def run_recommendation(student_id: str, student_profile: Dict[str, Any]) -> Dict[str, Any]:
    prediction = predict_career(student_profile)
    assessment_session = build_assessment_session(student_id)
    result = {
        "student_id": student_id,
        "prediction": prediction,
        "assessment": assessment_session,
        "question_bank": get_question_bank_stats(),
    }
    save_assessment(student_id, result)
    return result
