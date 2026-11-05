import io
import os
import sys
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from backend.questions_engine.assessment_engine import (
    build_assessment_session,
    get_assessment_history,
    db_create_student,
    db_get_student_by_email,
    db_get_student,
    db_update_student_profile,
    grade_answers,
    save_assessment
)
from backend.gemini_llm.gemini_refine import align_prediction_with_department, gemini_final_prediction
from backend.ml_models.tests.predict import predict_career   # Fixed import

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
HTML_PATH = PROJECT_ROOT / "frontend" / "index.html"

app = FastAPI(title="Smart Career Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================== ROOT ROUTE (Serves Frontend) ======================
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main HTML frontend"""
    if HTML_PATH.exists():
        return FileResponse(HTML_PATH)
    else:
        return HTMLResponse(content="<h1>Frontend file not found. Check path: " + str(HTML_PATH) + "</h1>", status_code=404)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ====================== Existing Routes (unchanged) ======================
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    phone: str
    dob: str
    gender: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    student_id: str
    school_name: Optional[str] = None
    school_type: Optional[str] = None
    state: Optional[str] = None
    class_level: Optional[str] = None
    department: Optional[str] = None
    language: Optional[str] = None
    uploaded_results: Optional[str] = None


class SubmissionRequest(BaseModel):
    student_id: str
    answers: Dict[str, str]


@app.post("/signup")
def signup(data: SignupRequest):
    student_data = {
        "id": data.email,
        "name": data.name,
        "email": data.email,
        "password": data.password,
        "phone": data.phone,
        "dob": data.dob,
        "gender": data.gender,
        "class_level": "SSS 1",
        "department": "Science",
        "school_name": "",
        "school_type": "Government School",
        "state": "Lagos",
        "language": "English",
        "uploaded_results": "[]"
    }
    success = db_create_student(student_data)
    if not success:
        raise HTTPException(status_code=400, detail="A user with this email already exists.")
    return {"status": "success", "message": "User registered successfully.", "student_id": data.email}


@app.post("/login")
def login(data: LoginRequest):
    student = db_get_student_by_email(data.email)
    if not student or student.get("password") != data.password:
        raise HTTPException(status_code=400, detail="Invalid email or password.")
    
    student_profile = dict(student)
    student_profile.pop("password", None)
    return {"status": "success", "student": student_profile}


@app.post("/update_profile")
def update_profile(data: ProfileUpdateRequest):
    updates = {k: v for k, v in data.dict().items() if v is not None and k != "student_id"}
    if not updates:
        return {"status": "success", "message": "No updates provided."}

    success = db_update_student_profile(data.student_id, updates)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update profile.")
    return {"status": "success", "message": "Profile updated successfully."}


@app.post("/assessment/submit")
def submit_assessment(data: SubmissionRequest):
    scores = grade_answers(data.answers)
    student_row = db_get_student(data.student_id) or {}

    # Load grades from uploaded results if they exist
    import json
    db_grades = {}
    uploaded_results_str = student_row.get("uploaded_results")
    if uploaded_results_str:
        try:
            parsed = json.loads(uploaded_results_str)
            if isinstance(parsed, dict):
                db_grades = parsed.get("subject_grades") or {}
        except Exception:
            pass

    department = student_row.get("department", "Science") or "Science"

    # ── Grade numeric conversion ──────────────────────────────────────────────
    GRADE_NUM = {"A": 8, "B": 6, "C": 5, "D": 3, "E": 2, "F": 1}

    # Department → canonical subject groups mapping
    DEPT_SUBJECTS = {
        "Science": [
            "Physics", "Chemistry", "Biology", "Further_Mathematics",
            "Agricultural_Science", "Geography", "Technical_Drawing", "Computer_Studies",
        ],
        "Arts": [
            "Literature_In_English", "Government", "History",
            "Christian_Religious_Studies/Islamic_Studies", "Creative_Arts", "Yoruba", "Igbo_Hausa",
        ],
        "Commercial": [
            "Economics", "Financial_Accounting", "Commerce", "Marketing", "Government",
        ],
    }
    # Compulsory subjects present in all departments
    COMPULSORY = ["Mathematics", "English", "Civic_Education"]

    # All subjects the model was trained on (MUST match new_model.ipynb)
    all_subjects = [
        "Mathematics", "English", "Civic_Education", "Physics", "Chemistry",
        "Biology", "Further_Mathematics", "Agricultural_Science", "Geography",
        "Technical_Drawing", "Computer_Studies", "Yoruba", "Igbo_Hausa",
        "Data_Processing", "Literature_In_English", "Christian_Religious_Studies_Islamic_Studies",
        "Creative_Arts", "Economics", "Financial_Accounting", "Commerce",
        "Government", "Marketing", "French",
    ]

    # ── Resolve grades from db_grades ────────────────────────────────────────
    subject_grades = {}  # sub -> letter grade (A/B/C/D/E/F)
    for sub in all_subjects:
        # Try several key variants
        key_variants = [
            sub.lower().replace("/", "_").replace(" ", "_"),
            sub.lower(),
            sub,
            sub.lower().replace("_", " "),
        ]
        resolved = None
        for k in key_variants:
            v = db_grades.get(k)
            if v:
                resolved = str(v).strip().upper()
                break
        if resolved and resolved in GRADE_NUM:
            subject_grades[sub] = resolved
        else:
            # Sensible defaults per subject importance
            if sub in ("Mathematics", "English"):
                subject_grades[sub] = "B"
            else:
                subject_grades[sub] = "C"

    # ── Derive computed features ──────────────────────────────────────────────
    # 1. WAEC Credits: count subjects with C or above (grade ≥ 5)
    waec_credits = sum(
        1 for g in subject_grades.values() if GRADE_NUM.get(g, 0) >= 5
    )
    waec_credits = max(3, min(waec_credits, 9))  # clamp to realistic range

    # 2. CGPA derived from average grade score (mapped to 0–5 scale)
    dept_subs = DEPT_SUBJECTS.get(department, DEPT_SUBJECTS["Science"])
    relevant_subs = COMPULSORY + dept_subs
    grade_vals = [
        GRADE_NUM.get(subject_grades.get(s, "C"), 5)
        for s in relevant_subs
        if s in subject_grades
    ]
    avg_grade = (sum(grade_vals) / len(grade_vals)) if grade_vals else 5.0
    # Map 1-8 grade scale to 0-5 CGPA
    cgpa = round(min(5.0, max(0.5, (avg_grade / 8.0) * 5.0)), 2)

    # 3. Academic Strength from test performance + grade average
    apt = scores.get("aptitude_score_10", 5.0)
    cog = scores.get("cognitive_score_10", 5.0)
    combined_score = (avg_grade / 8.0 * 10 + apt + cog) / 3.0  # all on 0-10
    if combined_score >= 7.5:
        academic_strength = "Excellent"
    elif combined_score >= 6.0:
        academic_strength = "Good"
    elif combined_score >= 4.5:
        academic_strength = "Average"
    else:
        academic_strength = "Below Average"

    # 4. Best Subject Category: which group has highest average grade?
    group_scores = {}
    for dept_label, subs in DEPT_SUBJECTS.items():
        vals = [GRADE_NUM.get(subject_grades.get(s, "C"), 5) for s in subs if s in subject_grades]
        group_scores[dept_label] = sum(vals) / len(vals) if vals else 5.0
    best_subject_category = max(group_scores, key=group_scores.get)

    # 5. Course alignment: does department match best subject category?
    course_alignment = 1 if best_subject_category == department else 0

    # 6. Confidence level derived from test composite
    composite_test = (apt + cog) / 2.0
    if composite_test >= 8.0:
        confidence_level = "Very confident"
    elif composite_test >= 6.0:
        confidence_level = "Quite confident"
    elif composite_test >= 4.0:
        confidence_level = "Somewhat confident"
    else:
        confidence_level = "Not very confident"

    # 7. Career influence — derive from psychometric interest pattern
    psy_val = scores.get("psychometric_avg_5", 3.0)
    per_val = scores.get("sentiment_avg_5", 3.0)
    if psy_val >= 4.0:
        career_influence = "Personal passion"
    elif per_val >= 4.0:
        career_influence = "Family influence"
    elif composite_test >= 7.0:
        career_influence = "Financial considerations"
    else:
        career_influence = "Peer influence"

    # 8. Derive realistic age from DOB (default 16)
    student_age = 16
    dob_str = student_row.get("dob", "")
    if dob_str:
        try:
            from datetime import datetime, date
            dob_date = datetime.strptime(str(dob_str).strip()[:10], "%Y-%m-%d").date()
            student_age = max(13, min(25, (date.today() - dob_date).days // 365))
        except Exception:
            student_age = 16

    # ── Build full profile for ML model ──────────────────────────────────────
    # Keys MUST use underscores to match predict.py's _build_input_df normaliser
    profile = {
        "Gender": student_row.get("gender", "Male"),
        "Age": student_age,
        "School_Type": student_row.get("school_type", "Government School"),
        "Department": department,
        "Academic_Strength": academic_strength,
        "Best_Subject_Category": best_subject_category,
        "Current_Career_Satisfaction": confidence_level,
        "WAEC_Credits": waec_credits,
        "WAEC_Year": 2024,
        "CGPA": cgpa,
        "JAMB_Score": 200,
        "Intended_Career_Path": "Unknown",
        "Course_Alignment": course_alignment,
        "Confidence_Level": confidence_level,
        "Career_Influence": career_influence,
        "aptitude_score_10": apt,
        "cognitive_score_10": cog,
        "psychometric_avg_5": scores.get("psychometric_avg_5", 3.0),
        "sentiment_avg_5": scores.get("sentiment_avg_5", 3.0),
    }

    # Merge all subject grades into profile
    for sub in all_subjects:
        profile[sub] = subject_grades.get(sub, "UNKNOWN")

    xgb_result = predict_career(profile)
    xgb_result = align_prediction_with_department(xgb_result, profile)
    gemini_result = gemini_final_prediction(xgb_result, scores, profile)

    result = {
        "student_id": data.student_id,
        "prediction": xgb_result,
        "gemini_recommendation": gemini_result,
        "test_scores": scores,
        "profile_summary": {
            "department": department,
            "academic_strength": academic_strength,
            "best_subject_category": best_subject_category,
            "waec_credits": waec_credits,
            "cgpa": cgpa,
            "course_alignment": course_alignment,
        }
    }

    save_assessment(data.student_id, result)
    return result


@app.get("/assessment/{student_id}")
def assessment(student_id: str):
    return build_assessment_session(student_id)


@app.get("/history/{student_id}")
def history(student_id: str):
    return get_assessment_history(student_id)

@app.post("/upload_results")
async def upload_results(file: UploadFile = File(...), level: str = "SSS 1"):
    """Handle Excel upload and extract grades for ML model"""
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        def score_to_grade(val):
            val_str = str(val).strip().upper()
            if val_str in ['A', 'B', 'C', 'D', 'E', 'F']:
                return val_str
            try:
                score = float(val)
                if score >= 75:
                    return 'A'
                elif score >= 65:
                    return 'B'
                elif score >= 50:
                    return 'C'
                elif score >= 45:
                    return 'D'
                elif score >= 40:
                    return 'E'
                else:
                    return 'F'
            except ValueError:
                return 'C'

        # Find columns (case-insensitive)
        cols = [str(c).strip().lower() for c in df.columns]
        subject_col_idx = None
        score_col_idx = None
        
        for idx, col in enumerate(cols):
            if col == 'subject':
                subject_col_idx = idx
            elif col == 'score':
                score_col_idx = idx
                
        if subject_col_idx is None or score_col_idx is None:
            # Fallback search if exact names not found
            for idx, col in enumerate(cols):
                if 'subject' in col:
                    subject_col_idx = idx
                elif 'score' in col or 'grade' in col:
                    score_col_idx = idx

        if subject_col_idx is None or score_col_idx is None:
            raise HTTPException(status_code=400, detail="Excel file must contain 'Subject' and 'Score' columns.")

        grades = {}
        subject_mapping = {
            "mathematics": "Mathematics",
            "english": "English",
            "civic education": "Civic_Education",
            "physics": "Physics",
            "chemistry": "Chemistry",
            "biology": "Biology",
            "further mathematics": "Further_Mathematics",
            "agricultural science": "Agricultural_Science",
            "agrictultural science": "Agricultural_Science",  # accept common typo
            "geography": "Geography",
            "technical drawing": "Technical_Drawing",
            "computer studies": "Computer_Studies",
            "yoruba": "Yoruba",
            "igbo hausa": "Igbo_Hausa",
            "data processing": "Data_Processing",
            "literature in english": "Literature_In_English",
            "christian religious studies": "Christian_Religious_Studies",
            "islamic studies": "Islamic_Studies",
            "christian religious studies/islamic studies": "Christian_Religious_Studies/Islamic_Studies",
            "creative arts": "Creative_Arts",
            "economics": "Economics",
            "financial accounting": "Financial_Accounting",
            "commerce": "Commerce",
            "business studies": "Business_Studies",
            "government": "Government",
            "marketing": "Marketing",
            "history": "History",
            "fine art": "Fine_Art"
        }

        for _, row in df.iterrows():
            sub_val = row.iloc[subject_col_idx]
            score_val = row.iloc[score_col_idx]
            if pd.isna(sub_val) or pd.isna(score_val):
                continue
            
            sub_str = str(sub_val).strip().lower()
            if sub_str in subject_mapping:
                model_key = subject_mapping[sub_str].lower().replace(" ", "_")
                grades[model_key] = score_to_grade(score_val)

        # Ensure compulsory subjects exist for downstream processing
        compulsory = ["mathematics", "english", "civic_education"]
        for comp in compulsory:
            if comp not in grades:
                grades[comp] = "C"

        return {
            "status": "success",
            "grades": grades,
            "level": level,
            "message": "Results processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process Excel file: {str(e)}")




# Provide department -> subjects mapping (ensures compulsory subjects present)
@app.get("/department_subjects")
def department_subjects():
    mapping = {
        "Science": ["Mathematics","English","Civic Education","Physics","Chemistry","Biology","Further Mathematics","Geography", "Technical Drawing", "Agricultural Science"],
        "Arts": ["Mathematics","English","Civic Education","Literature in English","Government","History","Economics","Creative Arts", "Christian Religious Studies/Islamic Studies"],
        "Commercial": ["Mathematics","English","Civic Education","Economics","Financial Accounting","Commerce","Government","Marketing"]
    }
    # Ensure compulsory subjects appear at front
    for dept, subs in mapping.items():
        for comp in ["Mathematics","English","Civic Education"]:
            if comp not in subs:
                subs.insert(0, comp)
    return mapping


@app.post('/save_results')
def save_results(payload: Dict[str, Any]):
    """Persist uploaded results to student's profile.
    Accepts a payload dict containing student_id, level (optional), subject_grades (merged), manual_grades, file_grades.
    The full payload is stored as JSON in the uploaded_results field for later retrieval.
    """
    try:
        student_id = payload.get('student_id')
        if not student_id:
            raise HTTPException(status_code=400, detail='student_id is required')
        # Normalize payload pieces
        level = payload.get('level') or ''
        subject_grades = payload.get('subject_grades') or {}
        manual_grades = payload.get('manual_grades') or {}
        file_grades = payload.get('file_grades') or {}

        import json
        
        # Fetch existing uploaded results
        existing_student = db_get_student(student_id)
        existing_uploaded_str = existing_student.get("uploaded_results") if existing_student else None
        
        uploaded_levels = []
        merged_subject_grades = {}
        merged_manual_grades = {}
        merged_file_grades = {}
        
        if existing_uploaded_str:
            try:
                existing_data = json.loads(existing_uploaded_str)
                if isinstance(existing_data, dict):
                    uploaded_levels = existing_data.get('uploaded_levels') or []
                    # Fallback for old schema level field
                    if not uploaded_levels and existing_data.get('level'):
                        uploaded_levels = [existing_data.get('level')]
                    merged_subject_grades = existing_data.get('subject_grades') or {}
                    merged_manual_grades = existing_data.get('manual_grades') or {}
                    merged_file_grades = existing_data.get('file_grades') or {}
                elif isinstance(existing_data, list):
                    uploaded_levels = existing_data
            except Exception:
                pass
                
        # Merge new data
        if level and level not in uploaded_levels:
            uploaded_levels.append(level)
            
        merged_subject_grades.update(subject_grades)
        merged_manual_grades.update(manual_grades)
        merged_file_grades.update(file_grades)

        uploaded_payload = {
            'level': level,  # keep for backwards compatibility
            'uploaded_levels': uploaded_levels,
            'subject_grades': merged_subject_grades,
            'manual_grades': merged_manual_grades,
            'file_grades': merged_file_grades
        }
        success = db_update_student_profile(student_id, {'uploaded_results': json.dumps(uploaded_payload)})
        if not success:
            raise HTTPException(status_code=500, detail='Failed to save results to profile')
        return {'status': 'success', 'message': 'Results saved'}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
