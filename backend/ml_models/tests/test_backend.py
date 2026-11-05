import sys
import os
import pytest
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette.testclient")
from fastapi.testclient import TestClient


# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backend.fastapi_integration.main import app
from backend.gemini_llm.gemini_refine import (
    _ensure_summary_career_alignment,
    align_prediction_with_department,
)
from backend.ml_models.tests.predict import predict_career
from backend.questions_engine.assessment_engine import (
    build_assessment_session,
    grade_answers,
    _ensure_db,
    _load_question_bank,
    db_create_student,
    db_get_student
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    import sqlite3
    from backend.questions_engine.assessment_engine import DB_PATH
    if DB_PATH.exists():
        try:
            os.remove(DB_PATH)
        except:
            pass
    _ensure_db()


def test_prediction_returns_structure():
    sample = {
        'Gender': 'Male', 'Age': '20', 'School_Type': 'Government School',
        'Department': 'Science', 'Mathematics': 'C', 'English': 'B',
        'Physics': 'E', 'Chemistry': 'A', 'Biology': 'A',
        'Academic Strength': 'High', 'Best Subject Category': 'Science',
        'WAEC Credits': 5, 'CGPA': 3.2,
        'Aptitude Score 10': 8, 'Cognitive Score 10': 7,
        'Psychometric Avg 5': 4.0, 'Sentiment Avg 5': 3.9,
    }
    result = predict_career(sample)
    assert 'predicted_career' in result
    assert 'confidence_percent' in result
    assert 'top_3' in result


def test_department_alignment_blocks_cross_department_primary():
    profile = {
        "Department": "Science",
        "Mathematics": "A",
        "English": "B",
        "Physics": "B",
        "Chemistry": "A",
        "Biology": "A",
    }
    raw_prediction = {
        "predicted_career": "Entrepreneurship & Management",
        "confidence_percent": 91.0,
        "top_3": [
            {"career": "Entrepreneurship & Management", "confidence_percent": 91.0},
            {"career": "Business & Finance", "confidence_percent": 6.0},
            {"career": "Medicine & Health Sciences", "confidence_percent": 3.0},
        ],
    }

    aligned = align_prediction_with_department(raw_prediction, profile)

    assert aligned["predicted_career"] == "Medicine & Health Sciences"
    assert aligned["top_3"][0]["career"] == aligned["predicted_career"]
    assert "Entrepreneurship & Management" not in [item["career"] for item in aligned["top_3"]]
    assert aligned["original_predicted_career"] == "Entrepreneurship & Management"


def test_mentor_heading_is_forced_to_primary_career():
    summary = "### Career Pathway: Entrepreneurship & Management\n\nAdvice body."
    aligned = _ensure_summary_career_alignment(summary, "Medicine & Health Sciences")

    assert aligned.startswith("### Career Pathway: Medicine & Health Sciences")
    assert "### Career Pathway: Entrepreneurship & Management" not in aligned


def test_assessment_session_contains_questions():
    session = build_assessment_session('test-student@example.com')
    assert session['student_id'] == 'test-student@example.com'
    assert len(session['tests']) == 4
    for test in session['tests']:
        assert len(test['questions']) == 10


def test_assessment_sessions_shuffle_questions_and_mcq_options():
    session_a = build_assessment_session('shuffle-test@example.com', shuffle_seed='login-a')
    session_b = build_assessment_session('shuffle-test@example.com', shuffle_seed='login-b')

    ids_a = [
        q["id"]
        for test in session_a["tests"]
        for q in test["questions"]
    ]
    ids_b = [
        q["id"]
        for test in session_b["tests"]
        for q in test["questions"]
    ]

    assert ids_a != ids_b

    bank = {q["id"]: q for q in _load_question_bank()}
    mcq_questions = [
        q
        for test in session_a["tests"]
        if test["category"] in {"aptitude", "cognitive"}
        for q in test["questions"]
    ]

    assert any(q["options"] != bank[q["id"]]["options"] for q in mcq_questions)


def test_assessment_questions_are_department_tailored():
    db_create_student({
        "id": "arts-student@example.com",
        "name": "Arts Student",
        "email": "arts-student@example.com",
        "password": "password123",
        "phone": "08000000000",
        "dob": "2010-01-01",
        "gender": "Female",
        "class_level": "SSS 2",
        "department": "Arts",
        "school_name": "",
        "school_type": "Government School",
        "state": "Lagos",
        "language": "English",
        "uploaded_results": "[]",
    })

    session = build_assessment_session('arts-student@example.com', shuffle_seed='arts-login')
    for test in session["tests"]:
        categories = {q["subject_category"] for q in test["questions"]}
        assert categories <= {"Arts", "General"}


def test_grading_logic():
    answers = {
        "aptitude-1": "3 days", "aptitude-2": "40 cm²",
        "cognitive-1": "15", "cognitive-2": "wrong",
        "psychometric-1": "Strongly agree", "psychometric-2": "Agree",
        "personality-1": "Always", "personality-2": "Often", "personality-3": "Never"
    }
    scores = grade_answers(answers)
    assert scores["aptitude_score_10"] == 10.0
    assert scores["cognitive_score_10"] == 5.0
    assert abs(scores["psychometric_avg_5"] - 4.5) < 0.1
    assert abs(scores["sentiment_avg_5"] - 3.33) < 0.1


def test_signup_login_flow():
    signup_data = {
        "name": "Test User", "email": "test@example.com", "password": "securepass123",
        "phone": "08012345678", "dob": "2010-01-01", "gender": "Male"
    }
    res = client.post("/signup", json=signup_data)
    assert res.status_code in [200, 201]

    # Login
    login_data = {"email": "test@example.com", "password": "securepass123"}
    res_login = client.post("/login", json=login_data)
    assert res_login.status_code == 200


def test_profile_update_and_submit():
    # Signup first
    signup_data = {
        "name": "Ada Obi",
        "email": "ada@example.com",
        "password": "password123",
        "phone": "09011112222",
        "dob": "2009-08-12",
        "gender": "Female"
    }
    client.post("/signup", json=signup_data)
    
    # Update profile info
    update_data = {
        "student_id": "ada@example.com",
        "school_name": "Queen's College Lagos",
        "school_type": "Federal Government College",
        "state": "Lagos",
        "class_level": "SSS 2",
        "department": "Commercial",
        "language": "English",
        "uploaded_results": '{"uploaded_levels": ["SSS 1"], "subject_grades": {"mathematics": "A", "english": "B", "economics": "A"}}'
    }
    res_update = client.post("/update_profile", json=update_data)
    assert res_update.status_code == 200
    
    # Verify updates in db
    student_row = db_get_student("ada@example.com")
    assert student_row["school_name"] == "Queen's College Lagos"
    assert student_row["department"] == "Commercial"
    
    # Get questions
    res_assess = client.get("/assessment/ada@example.com")
    assert res_assess.status_code == 200
    session_data = res_assess.json()
    assert len(session_data["tests"]) == 4
    
    # Submit answers
    answers = {}
    for test in session_data["tests"]:
        for q in test["questions"]:
            # Answer 'A' for MCQs, or 'Agree'/'Often' for Likert
            if test["category"] in ["aptitude", "cognitive"]:
                answers[q["id"]] = q["options"][0]
            elif test["category"] == "psychometric":
                answers[q["id"]] = "Agree"
            else:
                answers[q["id"]] = "Often"
                
    submit_data = {
        "student_id": "ada@example.com",
        "answers": answers
    }
    
    res_submit = client.post("/assessment/submit", json=submit_data)
    assert res_submit.status_code == 200
    res_json = res_submit.json()
    
    assert res_json["student_id"] == "ada@example.com"
    assert "prediction" in res_json
    assert "gemini_recommendation" in res_json
    assert "test_scores" in res_json
    assert res_json["prediction"]["predicted_career"]
    
    # Check history contains item
    res_history = client.get("/history/ada@example.com")
    assert res_history.status_code == 200
    assert len(res_history.json()) == 1
    assert res_history.json()[0]["payload"]["prediction"]["predicted_career"]


def test_science_submission_prediction_matches_mentor_advice(monkeypatch):
    monkeypatch.setattr("backend.gemini_llm.gemini_refine.GEMINI_API_KEY", None)

    signup_data = {
        "name": "Chidi Okafor",
        "email": "chidi@example.com",
        "password": "password123",
        "phone": "08022223333",
        "dob": "2010-03-18",
        "gender": "Male"
    }
    client.post("/signup", json=signup_data)

    update_data = {
        "student_id": "chidi@example.com",
        "school_type": "Private School",
        "class_level": "SSS 2",
        "department": "Science",
        "uploaded_results": (
            '{"uploaded_levels": ["SSS 1"], "subject_grades": {'
            '"mathematics": "A", "english": "B", "physics": "B", '
            '"chemistry": "A", "biology": "A", "computer_studies": "B"'
            '}}'
        )
    }
    assert client.post("/update_profile", json=update_data).status_code == 200

    session_data = client.get("/assessment/chidi@example.com").json()
    answers = {}
    for test in session_data["tests"]:
        for q in test["questions"]:
            if test["category"] in ["aptitude", "cognitive"]:
                answers[q["id"]] = q.get("answer", q["options"][0])
            elif test["category"] == "psychometric":
                answers[q["id"]] = "Strongly agree"
            else:
                answers[q["id"]] = "Often"

    response = client.post(
        "/assessment/submit",
        json={"student_id": "chidi@example.com", "answers": answers},
    )

    assert response.status_code == 200
    payload = response.json()
    primary = payload["prediction"]["predicted_career"]
    top_paths = [item["career"] for item in payload["prediction"]["top_3"]]
    mentor_summary = payload["gemini_recommendation"]["summary"]

    assert primary == "Medicine & Health Sciences"
    assert top_paths[0] == primary
    assert "Entrepreneurship & Management" not in top_paths
    assert f"### Career Pathway: {primary}" in mentor_summary


def test_excel_upload_parsing():
    import io
    import pandas as pd
    
    # Create a mock Excel sheet using the Subject and Score column structure
    df = pd.DataFrame({
        "Subject": ["Mathematics", "English", "Civic Education", "Physics", "Chemistry"],
        "Score": [90, 78, 62, 48, 35],
        "Exam Date": ["2026-07-10", "2026-07-10", "2026-07-10", "2026-07-10", "2026-07-10"]
    })
    
    out = io.BytesIO()
    df.to_excel(out, index=False)
    out.seek(0)
    
    # Post the file to /upload_results
    response = client.post(
        "/upload_results",
        files={"file": ("test.xlsx", out, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"level": "SSS 1"}
    )
    
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "success"
    grades = res_json["grades"]
    
    # Assert score-to-grade mappings
    assert grades["mathematics"] == "A"         # 90 -> A
    assert grades["english"] == "A"             # 78 -> A
    assert grades["civic_education"] == "C"     # 62 -> C
    assert grades["physics"] == "D"             # 48 -> D
    assert grades["chemistry"] == "F"           # 35 -> F

