"""
predict.py — Smart Career Predictor inference module.

Feature columns MUST exactly match those used during model training
(see backend/ml_models/training/new_model.ipynb).

Training pipeline columns:
  Numerical : age, waec_year, waec_credits, cgpa, course_alignment,
               aptitude_score_10, cognitive_score_10, psychometric_avg_5,
               sentiment_avg_5
  Categorical: gender, school_type, department, academic_strength,
               best_subject_category, confidence_level, career_influence,
               + 22 subject grade columns (A–F / UNKNOWN)
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# ── Model Loading ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR.parent.parent / "model_artifacts" / "xgb_best_model.pkl"
LABEL_ENCODER_PATH = BASE_DIR.parent.parent / "model_artifacts" / "label_encoder.pkl"

model = joblib.load(MODEL_PATH)
le = joblib.load(LABEL_ENCODER_PATH)

# ── Exact feature lists as trained (see backend/ml_models/training/new_model.ipynb) ──
SUBJECTS_COLS = [
    "mathematics", "english", "civic_education", "physics", "chemistry", "biology",
    "further_mathematics", "agricultural_science", "geography", "technical_drawing",
    "computer_studies", "yoruba", "igbo_hausa", "data_processing",
    "literature_in_english", "christian_religious_studies_islamic_studies",
    "creative_arts", "economics", "financial_accounting", "commerce",
    "government", "marketing", "french", "intended_career_path"
]

CATEGORICAL_COLUMNS = [
    "gender", "school_type", "department", "academic_strength",
    "best_subject_category", "current_career_satisfaction", "career_influence"
] + SUBJECTS_COLS

NUMERICAL_COLUMNS = [
    "waec_year", "waec_credits", "cgpa", "jamb_score"
]

ALL_FEATURES = CATEGORICAL_COLUMNS + NUMERICAL_COLUMNS

# Valid WAEC grade tokens
_VALID_GRADES = {"A", "B", "C", "D", "E", "F"}

# Map extended grade codes to simplified A–F
_GRADE_ALIAS = {
    "A1": "A", "B2": "A", "B3": "B", "C4": "B", "C5": "C", "C6": "C",
    "D7": "D", "E8": "E", "F9": "F",
}


def _normalise_grade(raw) -> str:
    """Normalise any grade value to a single uppercase letter or UNKNOWN."""
    s = str(raw).strip().upper()
    if s in ("NAN", "NONE", "", "NULL"):
        return "UNKNOWN"
    # Try aliased form first
    if s in _GRADE_ALIAS:
        return _GRADE_ALIAS[s]
    # Valid single-letter grade
    if s in _VALID_GRADES:
        return s
    # Truncate to first letter if multi-char (e.g., "A1" already handled above)
    if s and s[0] in _VALID_GRADES:
        return s[0]
    return "UNKNOWN"


def _build_input_df(input_data: dict) -> pd.DataFrame:
    """
    Convert the raw input dict into a DataFrame with exactly the columns
    expected by the Pipeline, in the correct order.
    """
    # Normalise keys: strip, lowercase, replace spaces with underscores, replace slashes
    raw = {
        k.strip().lower().replace(" ", "_").replace("/", "_").replace("__", "_"): v
        for k, v in input_data.items()
    }

    row = {}

    # ── Categorical: profile fields ───────────────────────────────────────────
    cat_fields = [
        "gender", "school_type", "department", "academic_strength",
        "best_subject_category", "current_career_satisfaction", "career_influence"
    ]
    for col in cat_fields:
        val = raw.get(col)
        if val is None or str(val).strip().lower() in ("none", "nan", "", "0", "0.0"):
            row[col] = "Unknown"
        else:
            row[col] = str(val).strip()

    # ── Subject grade columns & non-grade subject categories ───────────────
    for col in SUBJECTS_COLS:
        val = raw.get(col)
        if col == "intended_career_path":
            if val is None or str(val).strip().lower() in ("none", "nan", "", "0", "0.0"):
                row[col] = "Unknown"
            else:
                row[col] = str(val).strip()
        else:
            row[col] = _normalise_grade(val if val is not None else "UNKNOWN")

    # ── Numerical columns ──────────────────────────────────────────────────────
    num_defaults = {
        "waec_year": 2024.0,
        "waec_credits": 5.0,
        "cgpa": 3.0,
        "jamb_score": 200.0,
    }
    for col, default in num_defaults.items():
        raw_val = raw.get(col)
        try:
            row[col] = float(raw_val) if raw_val is not None and str(raw_val).strip() != "" else float(default)
        except (ValueError, TypeError):
            row[col] = float(default)

    # Build DataFrame with ALL_FEATURES column order
    df = pd.DataFrame([row], columns=ALL_FEATURES)

    # Ensure correct dtypes
    for col in NUMERICAL_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in CATEGORICAL_COLUMNS:
        df[col] = df[col].astype(object)

    return df


def predict_career(input_data: dict) -> dict:
    """
    Predict career path from a student profile dict.

    Required keys (case-insensitive, spaces normalised to underscores):
      gender, school_type, department

    Optional keys:
      academic_strength, best_subject_category, confidence_level,
      career_influence, subject grades (A–F), numerical scores

    Returns:
      {
        "predicted_career": str,
        "confidence_percent": float,
        "top_3": [{"career": str, "confidence_percent": float}, ...]
      }
    """
    df_input = _build_input_df(input_data)

    pred_encoded = model.predict(df_input)[0]
    proba = model.predict_proba(df_input)[0]

    career = le.inverse_transform([pred_encoded])[0]
    confidence = float(np.max(proba))
    top_three = sorted(
        zip(le.classes_, proba), key=lambda x: x[1], reverse=True
    )[:3]

    return {
        "predicted_career": str(career),
        "confidence_percent": float(round(confidence * 100, 1)),
        "top_3": [
            {
                "career": str(c),
                "confidence_percent": float(round(float(p) * 100, 1)),
            }
            for c, p in top_three
        ],
    }


def transform_for_model(input_data: dict) -> pd.DataFrame:
    """Return the preprocessed DataFrame used by the model for debugging."""
    return _build_input_df(input_data)


# ── Quick smoke test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    science_sample = {
        "Gender": "Male",
        "School_Type": "Private School",
        "Department": "Science",
        "Mathematics": "A",
        "English": "A",
        "Physics": "A",
        "Chemistry": "A",
        "Biology": "A",
        "Further_Mathematics": "A",
        "Computer_Studies": "A",
        "Academic_Strength": "High",
        "Best_Subject_Category": "Science",
        "Confidence_Level": "Very confident",
        "Career_Influence": "Personal passion",
        "Age": 18,
        "WAEC_Year": 2024,
        "WAEC_Credits": 8,
        "CGPA": 4.5,
        "aptitude_score_10": 9,
        "cognitive_score_10": 9,
        "psychometric_avg_5": 4.5,
        "sentiment_avg_5": 4.5,
        "course_alignment": 1,
    }

    arts_sample = {
        "Gender": "Female",
        "School_Type": "Government School",
        "Department": "Arts",
        "Mathematics": "C",
        "English": "A",
        "Literature_In_English": "A",
        "Government": "A",
        "Christian_Religious_Studies/Islamic_Studies": "B",
        "Creative_Arts": "A",
        "Academic_Strength": "High",
        "Best_Subject_Category": "Arts",
        "Confidence_Level": "Very confident",
        "Career_Influence": "Personal passion",
        "Age": 17,
        "WAEC_Year": 2024,
        "WAEC_Credits": 7,
        "CGPA": 4.0,
        "aptitude_score_10": 7,
        "cognitive_score_10": 8,
        "psychometric_avg_5": 4.0,
        "sentiment_avg_5": 4.0,
        "course_alignment": 1,
    }

    commercial_sample = {
        "Gender": "Male",
        "School_Type": "Mission / Faith School",
        "Department": "Commercial",
        "Mathematics": "B",
        "English": "A",
        "Economics": "A",
        "Financial_Accounting": "A",
        "Commerce": "A",
        "Marketing": "A",
        "Academic_Strength": "High",
        "Best_Subject_Category": "Commercial",
        "Confidence_Level": "Very confident",
        "Career_Influence": "Financial considerations",
        "Age": 19,
        "WAEC_Year": 2024,
        "WAEC_Credits": 7,
        "CGPA": 4.2,
        "aptitude_score_10": 8,
        "cognitive_score_10": 8,
        "psychometric_avg_5": 4.0,
        "sentiment_avg_5": 4.0,
        "course_alignment": 1,
    }

    for label, sample in [
        ("Science (All A, High CGPA)", science_sample),
        ("Arts (Strong Literature/Govt)", arts_sample),
        ("Commercial (Strong Business Subjects)", commercial_sample),
    ]:
        result = predict_career(sample)
        print(f"\n=== {label} ===")
        print(f"Predicted: {result['predicted_career']} ({result['confidence_percent']}%)")
        for item in result["top_3"]:
            print(f"  • {item['career']}: {item['confidence_percent']}%")