import os
import sys
import logging
import re
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root (ml/) is on sys.path for cross-package imports
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.ml_models.tests.predict import predict_career

load_dotenv()

logger = logging.getLogger(__name__)

# Prefer the modern Google GenAI package, but fall back to the deprecated google-generativeai API
genai = None
genai_client = None
_genai_is_modern = False
_genai_supports_generative_model = False

try:
    import google.genai as _genai
    genai = _genai
    _genai_is_modern = hasattr(genai, "Client")
    _genai_supports_generative_model = hasattr(genai, "GenerativeModel")
except Exception:
    try:
        import google.generativeai as _genai
        genai = _genai
        _genai_is_modern = False
        _genai_supports_generative_model = hasattr(genai, "GenerativeModel")
    except Exception:
        logger.warning("Google Generative AI client library is not installed or cannot be imported.")

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if GEMINI_API_KEY and genai is not None:
    if _genai_is_modern and hasattr(genai, "Client"):
        try:
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as exc:
            logger.warning("Failed to initialize Google GenAI client: %s", exc)
            genai_client = None
    elif hasattr(genai, "configure"):
        genai.configure(api_key=GEMINI_API_KEY)
    elif _genai_supports_generative_model:
        # Older google-generativeai clients use model-level configuration with a global API key.
        logger.info("Using legacy Google Generative AI client without explicit client initialization.")
    else:
        logger.warning("Loaded Google GenAI library but could not configure an API client.")

# Define static local career recommendations for the 10 target classes
LOCAL_CAREER_GUIDANCE = {
    "Agriculture & Environmental Sciences": {
        "description": "This path is focused on modern food production, biotechnology, smart farming, and environmental management. Nigeria's agricultural sector is undergoing a technology revolution, offering opportunities in agribusiness, soil science, forestry, and sustainable resource management.",
        "actionable_steps": [
            "Focus on biology, chemistry, and agricultural science in your school curriculum.",
            "Read about modern agricultural techniques such as vertical farming, soil-less cultivation (hydroponics), and drone technology in agriculture.",
            "Prepare for the JAMB examinations focusing on English, Biology, Chemistry, and Agricultural Science/Physics."
        ]
    },
    "Business & Finance": {
        "description": "This path covers financial management, accounting, corporate finance, investment banking, and the rapidly growing fintech sector in Nigeria. Roles in this field are crucial for running corporate enterprises, banking institutions, and venture funds.",
        "actionable_steps": [
            "Focus on mathematics, economics, financial accounting, and commerce in school.",
            "Read local and international financial news (e.g. BusinessDay, fintech blogs) to understand banking, inflation, and investment.",
            "Practice quantitative analysis and analytical reasoning, and prepare for JAMB (English, Mathematics, Economics, and Financial Accounting/Commerce)."
        ]
    },
    "Computer Science & IT": {
        "description": "This path deals with software engineering, cybersecurity, data science, networking, and system administration. Nigeria's technology ecosystem is one of the most vibrant on the continent, offering tremendous careers in tech hubs like Yaba and Ikeja.",
        "actionable_steps": [
            "Prioritize mathematics, further mathematics, and computer studies in your academic work.",
            "Start learning coding basics (like Python, HTML/CSS, or JavaScript) through free portals like freeCodeCamp, W3Schools, or Sololearn.",
            "Build small software scripts, participate in coding clubs or competitions, and prepare for JAMB (English, Mathematics, Physics, and Chemistry)."
        ]
    },
    "Creative Arts & Design": {
        "description": "This path embraces graphic design, fine arts, fashion, music production, digital animation, and user interface (UI/UX) design. Nigeria's Nollywood, Afrobeat, and design industries are globally recognized, offering rewarding paths for creative minds.",
        "actionable_steps": [
            "Build a personal portfolio of your sketches, digital art designs, creative writing, or music mixes.",
            "Learn digital design software such as Figma, Canva, or Photoshop through free YouTube tutorials.",
            "Select creative arts and literature in school, and select JAMB subjects in the arts/humanities track."
        ]
    },
    "Education & Humanities": {
        "description": "This path is dedicated to teaching, history, languages, philosophy, and human services. It prepares you for careers in educational planning, public relations, writing, educational technology, and school leadership.",
        "actionable_steps": [
            " excel in literature-in-english, history, and local languages (Yoruba/Igbo/Hausa).",
            "Volunteer to tutor junior students in your school or community to build your teaching and communication skills.",
            "Plan your JAMB subject combination with English, Literature, Christian/Islamic studies or History, and Government."
        ]
    },
    "Engineering & Technology": {
        "description": "This path involves civil, electrical, mechanical, mechanical, and chemical engineering. It focuses on design, construction, robotics, power systems, and infrastructure development, which are essential for Nigeria's development.",
        "actionable_steps": [
            "Maintain strong grades in mathematics, further mathematics, physics, and chemistry.",
            "Read about how machines work, build physical models (e.g., electronic boards, small structural models), and join your school's Jet Club.",
            "Prepare for JAMB by mastering English, Mathematics, Physics, and Chemistry."
        ]
    },
    "Entrepreneurship & Management": {
        "description": "This path concentrates on building startups, project management, sales, marketing, and corporate administration. It teaches you how to coordinate teams, manage business budgets, and grow small-to-medium businesses.",
        "actionable_steps": [
            "Focus on commerce, marketing, economics, and civic education.",
            "Take the lead in group school projects, and read books on leadership, time management, and business operations.",
            "Practice writing simple business pitches, and select commerce/marketing and economics for JAMB."
        ]
    },
    "Law & Social Sciences": {
        "description": "This path explores legal frameworks, human rights, sociology, political science, and international relations. Lawyers and social scientists in Nigeria play critical roles in corporate counsel, civil rights, policy-making, and diplomacy.",
        "actionable_steps": [
            "Focus heavily on literature-in-english, government, civic education, and history.",
            "Join your school's debating society, press club, or mock trials to improve public speaking, logical analysis, and essay writing.",
            "Select JAMB subject combination of English, Literature, Government, and Christian/Islamic studies or Economics."
        ]
    },
    "Mass Communication & Media": {
        "description": "This path centers on journalism, broadcasting, public relations, and digital content creation. It is vital for news networks, radio stations, digital media, advertising agencies, and corporate communications in Nigeria.",
        "actionable_steps": [
            "Practice writing articles, blogs, or scripting short videos, and work on public speaking or broadcasting skills.",
            "Learn basic video/audio editing tools (like CapCut, Audacity, or Premiere Pro) and write for the school press club.",
            "Select English, Literature, Government, and an arts/social science elective for JAMB."
        ]
    },
    "Medicine & Health Sciences": {
        "description": "This path covers medicine, pharmacy, nursing, dentistry, medical lab sciences, and public health. Highly prestigious and critically needed, it offers opportunities to save lives in hospitals and health-tech startups.",
        "actionable_steps": [
            "Maintain exceptional grades in biology, chemistry, physics, and mathematics.",
            "Read about anatomy, basic healthcare practices, and first aid, or volunteer/observe at a local clinic if possible.",
            "Ensure you choose JAMB subjects: English, Biology, Chemistry, and Physics."
        ]
    }
}


# Department → preferred career paths mapping (high-accuracy fallback)
DEPT_CAREER_MAP = {
    "Science": {
        "default": "Engineering & Technology",
        "high_bio_chem": "Medicine & Health Sciences",
        "high_math_physics": "Computer Science & IT",
        "high_agric": "Agriculture & Environmental Sciences",
    },
    "Arts": {
        "default": "Education & Humanities",
        "high_govt_civic": "Law & Social Sciences",
        "high_lit_english": "Mass Communication & Media",
        "high_creative": "Creative Arts & Design",
    },
    "Commercial": {
        "default": "Business & Finance",
        "high_marketing": "Entrepreneurship & Management",
        "high_econ_accounts": "Business & Finance",
    },
}

# Minimum subject scores that trigger specialist override
GRADE_NUM = {"A": 6, "B": 5, "C": 4, "D": 3, "E": 2, "F": 1, "UNKNOWN": 7}

DEPARTMENT_CAREER_OPTIONS = {
    "Science": [
        "Medicine & Health Sciences",
        "Engineering & Technology",
        "Computer Science & IT",
        "Agriculture & Environmental Sciences",
    ],
    "Arts": [
        "Law & Social Sciences",
        "Mass Communication & Media",
        "Creative Arts & Design",
        "Education & Humanities",
    ],
    "Commercial": [
        "Business & Finance",
        "Entrepreneurship & Management",
    ],
}


def _normalise_department(value):
    """Return one of the known department labels."""
    raw = str(value or "Science").strip().lower()
    for dept in DEPARTMENT_CAREER_OPTIONS:
        if raw == dept.lower():
            return dept
    return "Science"


def _get_subject_num(profile, sub):
    """Return numeric grade value for a subject in the profile."""
    val = profile.get(sub)
    if val is None:
        alt_sub = sub.replace("/", "_") if "/" in sub else sub.replace("_", "/")
        val = profile.get(alt_sub, "C")
    grade_str = str(val).strip().upper()
    return GRADE_NUM.get(grade_str, 5)


def _override_career_by_department(profile):
    """
    Department + subject-grade-aware career override.
    Returns the most appropriate career string, or None to keep the ML result.
    """
    dept = _normalise_department(profile.get("Department", "Science"))
    
    if dept == "Science":
        bio = _get_subject_num(profile, "Biology")
        chem = _get_subject_num(profile, "Chemistry")
        math = _get_subject_num(profile, "Mathematics")
        phys = _get_subject_num(profile, "Physics")
        comp = _get_subject_num(profile, "Computer_Studies")
        fm = _get_subject_num(profile, "Further_Mathematics")
        agric = _get_subject_num(profile, "Agricultural_Science")

        # Strong bio+chem → Medicine
        if (bio + chem) >= 14:
            return "Medicine & Health Sciences"
        # Strong math+physics or CS → CS&IT
        if (math + phys + fm + comp) >= 24 or (comp + math) >= 14:
            return "Computer Science & IT"
        # Strong agric → Agriculture
        if agric >= 7:
            return "Agriculture & Environmental Sciences"
        return "Engineering & Technology"

    elif dept == "Arts":
        lit = _get_subject_num(profile, "Literature_In_English")
        govt = _get_subject_num(profile, "Government")
        hist = _get_subject_num(profile, "History")
        crs = _get_subject_num(profile, "Christian_Religious_Studies/Islamic_Studies")
        creative = _get_subject_num(profile, "Creative_Arts")

        # Strong governance/history → Law & Social Sciences
        if (govt + hist) >= 12:
            return "Law & Social Sciences"
        # Strong literature → Mass Communication
        if lit >= 7:
            return "Mass Communication & Media"
        # Strong creative arts
        if creative >= 7:
            return "Creative Arts & Design"
        return "Education & Humanities"

    elif dept == "Commercial":
        econ = _get_subject_num(profile, "Economics")
        acc = _get_subject_num(profile, "Financial_Accounting")
        mkt = _get_subject_num(profile, "Marketing")
        comm = _get_subject_num(profile, "Commerce")

        # Strong marketing → Entrepreneurship
        if mkt >= 7:
            return "Entrepreneurship & Management"
        # Strong econ + accounting → Finance
        if (econ + acc) >= 13:
            return "Business & Finance"
        return "Business & Finance"

    return None


def align_prediction_with_department(xgb_result, profile):
    """
    Make the ML result department-consistent before the frontend or mentor advice sees it.

    The trained model can occasionally return a confident cross-department class. This
    guard keeps recommendations useful for Nigerian SSS department tracks while still
    preserving model confidences for any department-valid options it found.
    """
    aligned = dict(xgb_result or {})
    dept = _normalise_department(profile.get("Department", "Science"))
    allowed = DEPARTMENT_CAREER_OPTIONS[dept]
    predicted = aligned.get("predicted_career") or allowed[0]
    confidence = float(aligned.get("confidence_percent") or 0.0)

    specialist = _override_career_by_department(profile) or allowed[0]
    must_override = (
        predicted not in allowed
        or str(predicted).startswith("None")
        or confidence < 50.0
    )
    effective = specialist if must_override else predicted

    original_top = aligned.get("top_3") or []
    by_career = {}
    for item in original_top:
        career = item.get("career")
        if career in allowed:
            by_career[career] = float(item.get("confidence_percent") or 0.0)

    if effective not in allowed:
        effective = allowed[0]

    if effective not in by_career:
        by_career[effective] = max(confidence, 70.0 if must_override else confidence)

    # Fill department-relevant alternatives so the UI never displays a
    # cross-department primary, secondary, or broader option.
    floor_scores = [68.0, 61.0, 54.0, 48.0]
    for index, career in enumerate(allowed):
        by_career.setdefault(career, floor_scores[min(index, len(floor_scores) - 1)])

    ordered = [effective] + [
        career for career, _ in sorted(
            by_career.items(), key=lambda item: item[1], reverse=True
        )
        if career != effective
    ]

    aligned["predicted_career"] = effective
    aligned["confidence_percent"] = round(float(by_career.get(effective, confidence)), 1)
    aligned["top_3"] = [
        {
            "career": career,
            "confidence_percent": round(float(by_career[career]), 1),
        }
        for career in ordered[:3]
    ]
    aligned["department"] = dept
    aligned["department_career_options"] = allowed
    if must_override:
        aligned["override_applied"] = True
        aligned["original_predicted_career"] = predicted

    return aligned


def _ensure_summary_career_alignment(summary, career):
    """Keep the visible mentor advice heading aligned with the primary career."""
    heading = f"### Career Pathway: {career}"
    text = str(summary or "").strip()
    if not text:
        return heading

    pattern = r"(?im)^###\s+Career Pathway\s*:\s*.+$"
    if re.search(pattern, text):
        return re.sub(pattern, heading, text, count=1)
    return f"{heading}\n\n{text}"


def generate_local_fallback(xgb_result, test_scores, profile):
    xgb_result = align_prediction_with_department(xgb_result, profile)
    predicted_career = xgb_result.get("predicted_career", "Computer Science & IT")

    # Fallback to default if predicted_career is not in the guidance dict
    guidance = LOCAL_CAREER_GUIDANCE.get(predicted_career, LOCAL_CAREER_GUIDANCE["Computer Science & IT"])

    department = profile.get("Department", "Science")
    gender = profile.get("Gender", "Student")
    school_type = profile.get("School_Type", "Government School")
    academic_strength = profile.get("Academic_Strength", "Average")
    best_cat = profile.get("Best_Subject_Category", department)
    # cgpa = profile.get("CGPA", 3.0)
    waec_credits = profile.get("WAEC_Credits", 5)

    apt = test_scores.get("aptitude_score_10", 5.0)
    cog = test_scores.get("cognitive_score_10", 5.0)
    psy = test_scores.get("psychometric_avg_5", 3.0)
    per = test_scores.get("sentiment_avg_5", 3.0)

    # ── Identify student's top 3 strongest subjects ──────────────────────────
    subject_list = [
        "Mathematics", "English", "Physics", "Chemistry", "Biology",
        "Further_Mathematics", "Agricultural_Science", "Geography",
        "Computer_Studies", "Literature_In_English", "Government",
        "Economics", "Financial_Accounting", "Commerce", "Marketing",
        "Creative_Arts", "Civic_Education",
    ]
    sub_scores = [(s, GRADE_NUM.get(str(profile.get(s, "C")).upper(), 5)) for s in subject_list]
    sub_scores.sort(key=lambda x: x[1], reverse=True)
    top_subs = sub_scores[:3]
    best_sub = top_subs[0][0]

    # ── Career-specific JAMB combinations & Nigerian universities ────────────
    CAREER_JAMB = {
        "Agriculture & Environmental Sciences": {
            "jamb": "English, Biology, Chemistry, and Agricultural Science (or Physics)",
            "universities": "University of Agriculture Abeokuta (FUNAAB), Ahmadu Bello University Zaria, University of Ibadan",
            "scholarships": "NNPC/NAOC/OANDO JV Scholarship, Federal Government STEM Scholarship, AGRA Scholarship for Agricultural Sciences",
        },
        "Business & Finance": {
            "jamb": "English, Mathematics, Economics, and Accounting (or Commerce)",
            "universities": "University of Lagos (UNILAG), Covenant University, Obafemi Awolowo University (OAU)",
            "scholarships": "GTBank Scholarship, NNPC/Shell Scholarship, First Bank Endowment Fund",
        },
        "Computer Science & IT": {
            "jamb": "English, Mathematics, Physics, and Chemistry (or Biology)",
            "universities": "University of Lagos (UNILAG), Federal University of Technology Akure (FUTA), Covenant University, Obafemi Awolowo University",
            "scholarships": "Google Africa Developer Scholarship, MTN Foundation Scholarship, PTDF Overseas Scholarship, Andela Learning Community",
        },
        "Creative Arts & Design": {
            "jamb": "English, Literature in English, and two of Fine Arts/Government/CRS/Economics",
            "universities": "Yaba College of Technology, University of Lagos, Obafemi Awolowo University, Ahmadu Bello University",
            "scholarships": "TETFund Scholarship, British Council GREAT Scholarship, Creative Industry Initiative",
        },
        "Education & Humanities": {
            "jamb": "English, Literature in English, and two of Government/History/CRS/Economics",
            "universities": "University of Ibadan, University of Nigeria Nsukka (UNN), Lagos State University (LASU), Obafemi Awolowo University",
            "scholarships": "TETFund Scholarship, Agbami Scholarship, Federal Government Teacher Training Bursary",
        },
        "Engineering & Technology": {
            "jamb": "English, Mathematics, Physics, and Chemistry",
            "universities": "University of Lagos, Federal University of Technology Akure (FUTA), Ahmadu Bello University, University of Benin",
            "scholarships": "PTDF Scholarship, Shell/NNPC Scholarship, NNPC/Chevron JV Scholarship, Total E&P Scholarship",
        },
        "Entrepreneurship & Management": {
            "jamb": "English, Mathematics, Economics, and Commerce (or Accounting)",
            "universities": "Lagos Business School (LBS), University of Lagos, Covenant University, Babcock University",
            "scholarships": "Tony Elumelu Foundation Entrepreneurship Programme, Bank of Industry Youth Entrepreneurship Support, MTN Y'ello Foundation",
        },
        "Law & Social Sciences": {
            "jamb": "English, Literature in English, Government, and Economics (or CRS/History)",
            "universities": "University of Lagos, University of Ibadan, Obafemi Awolowo University, Nigerian Law School (post-LLB)",
            "scholarships": "Agbami Scholarship, NNPC/Total Scholarship, Federal Government Scholarship for Law",
        },
        "Mass Communication & Media": {
            "jamb": "English, Literature in English, Government, and Economics (or CRS)",
            "universities": "University of Lagos, University of Nigeria Nsukka, Lagos State University, Covenant University",
            "scholarships": "NLNG Scholarship, Media Trust Foundation, Nigerian Press Council Fellowship",
        },
        "Medicine & Health Sciences": {
            "jamb": "English, Biology, Chemistry, and Physics (or Mathematics)",
            "universities": "University of Ibadan (UI), University of Lagos (UNILAG), Obafemi Awolowo University (OAU), Ahmadu Bello University (ABU)",
            "scholarships": "NNPC/Total Scholarship, Agbami Medical Scholarship, BEA Scholarship, Federal Government Health Scholarship",
        },
    }

    career_info = CAREER_JAMB.get(predicted_career, CAREER_JAMB.get("Computer Science & IT"))

    # ── Build strengths analysis ─────────────────────────────────────────────
    strengths = []
    growth_areas = []

    # Aptitude analysis
    if apt >= 7.5:
        strengths.append(f"**Outstanding Logical Reasoning ({apt:.1f}/10)** — Your aptitude score places you in the top tier. You demonstrate exceptional ability in numerical reasoning, pattern recognition, and analytical problem-solving. This is a critical advantage for {predicted_career}.")
    elif apt >= 5.0:
        strengths.append(f"**Solid Analytical Thinking ({apt:.1f}/10)** — Your aptitude score shows capable logical reasoning skills. With targeted practice in mathematical problem-solving and abstract thinking, you can sharpen this further.")
    else:
        growth_areas.append(f"**Aptitude Development ({apt:.1f}/10)** — Focus on daily practice with logical reasoning puzzles, WAEC past questions (especially Mathematics), and apps like Brilliant.org to strengthen your analytical foundation.")

    # Cognitive analysis
    if cog >= 7.5:
        strengths.append(f"**Excellent Cognitive Processing ({cog:.1f}/10)** — You demonstrate rapid comprehension, strong working memory, and effective information processing. You'll excel at absorbing complex material in university-level {predicted_career} courses.")
    elif cog >= 5.0:
        strengths.append(f"**Good Cognitive Ability ({cog:.1f}/10)** — Your cognitive skills show steady information processing and learning capacity. Regular reading, memory exercises, and engaging with challenging material will help you improve.")
    else:
        growth_areas.append(f"**Cognitive Skill Building ({cog:.1f}/10)** — Strengthen your cognitive processing through active reading (newspapers, textbooks), crossword puzzles, and learning new skills like coding basics or a musical instrument.")

    # Psychometric analysis
    if psy >= 4.0:
        strengths.append(f"**Strong Career Motivation ({psy:.1f}/5)** — Your psychometric profile reveals deep intrinsic motivation, self-directed learning habits, and genuine passion. Students with this level of drive consistently outperform their peers in {predicted_career}.")
    elif psy >= 2.5:
        strengths.append(f"**Developing Professional Interest ({psy:.1f}/5)** — You show genuine curiosity about this career path. Engaging with professionals in {predicted_career} through mentorship or job shadowing will deepen your commitment.")
    else:
        growth_areas.append(f"**Career Exploration Needed ({psy:.1f}/5)** — Take time to explore different aspects of {predicted_career} through YouTube channels, career talks, and informational interviews with professionals in the field.")

    # Personality analysis
    if per >= 4.0:
        strengths.append(f"**Excellent Interpersonal & Organisational Skills ({per:.1f}/5)** — You work well with others, manage your time effectively, and show strong emotional intelligence. Collaborative and leadership roles in {predicted_career} are a natural fit for you.")
    elif per >= 2.5:
        strengths.append(f"**Balanced Work Style ({per:.1f}/5)** — You can adapt between independent work and team collaboration. Joining student organisations or group projects will help you build even stronger teamwork skills.")
    else:
        strengths.append(f"**Independent & Focused ({per:.1f}/5)** — You prefer deep, focused work and self-directed learning. Many specialist and research roles in {predicted_career} highly value this quality.")

    # Academic strengths
    top_sub_names = [s.replace('_', ' ') for s, _ in top_subs if _ >= 6]
    if top_sub_names:
        strengths.append(f"**Subject Strengths** — Your strongest subjects are **{', '.join(top_sub_names)}**, which directly support a career in {predicted_career}.")

    if best_cat == department:
        strengths.append(f"**Perfect Department Alignment** — Your highest-performing subject group ({best_cat}) aligns perfectly with your {department} department, maximising your readiness for {predicted_career}.")

    # CGPA commentary
    # if cgpa >= 4.0:
    #     strengths.append(f"**Strong Academic Record (CGPA: {cgpa:.2f}/5.0)** — Your grades position you competitively for direct entry into top Nigerian universities for {predicted_career}.")
    # elif cgpa >= 3.0:
    #     strengths.append(f"**Solid Academic Foundation (CGPA: {cgpa:.2f}/5.0)** — Your grades meet the requirements for most {predicted_career} programmes. Focus on excelling in your core subjects to strengthen your JAMB and Post-UTME performance.")
    # else:
    #     growth_areas.append(f"**Academic Improvement Needed (CGPA: {cgpa:.2f}/5.0)** — Prioritise improving your grades in core subjects. Consider enrolling in after-school tutorials, joining study groups, and practising with WAEC and JAMB past questions daily.")

    strengths_md = "\n".join([f"- {s}" for s in strengths])
    growth_md = "\n".join([f"- {g}" for g in growth_areas]) if growth_areas else ""
    steps_md = "\n".join([f"{i+1}. {step}" for i, step in enumerate(guidance["actionable_steps"])])

    # ── Compose the full report ──────────────────────────────────────────────
    summary = f"""### Career Pathway: {predicted_career}

{guidance['description']}

---

### Your Profile at a Glance
| Metric | Value |
|---|---|
| **Department** | {department} |
| **Academic Strength** | {academic_strength} |
| **Subject Credits (C and above)** | {waec_credits} subjects |
| **Best Subject Group** | {best_cat} |
| **School Type** | {school_type} |

---

### Your Key Strengths
{strengths_md}
"""

    if growth_md:
        summary += f"""
### Areas for Growth
{growth_md}
"""

    summary += f"""
---

### Your Personalised Action Plan
{steps_md}

---

### Recommended JAMB Subject Combination
**{career_info['jamb']}**

Choose this combination when registering for JAMB to qualify for {predicted_career} programmes at top universities.

### Top Nigerian Universities for {predicted_career}
{career_info['universities']}

### Scholarships to Explore
{career_info['scholarships']}

---

> **Remember:** Your career journey is unique to you. These recommendations are based on your academic profile, test performance, and personality traits. Stay consistent with your studies, seek mentorship from professionals in your chosen field, and never stop learning.

*— Smart Career Predictor, powered by AI and academic data analysis*"""

    return summary




def gemini_final_prediction(xgb_result, test_scores, profile):
    xgb_result = align_prediction_with_department(xgb_result, profile)
    confidence = xgb_result.get("confidence_percent", 0.0)
    effective_career = xgb_result.get("predicted_career", "Computer Science & IT")

    # Try calling Google Generative AI first
    if GEMINI_API_KEY and genai is not None:
        dept = profile.get("Department", "Science")
        DEPT_RELEVANT = {
            "Science": ["Mathematics", "English", "Physics", "Chemistry", "Biology", "Geography",
                        "Further_Mathematics", "Agricultural_Science", "Computer_Studies", "Technical_Drawing"],
            "Arts": ["Mathematics", "English", "Literature_In_English", "Government",
                     "History", "Creative_Arts"],
            "Commercial": ["Mathematics", "English", "Economics", "Financial_Accounting",
                           "Commerce", "Marketing", "Government"],
        }
        relevant_keys = DEPT_RELEVANT.get(dept, list(DEPT_RELEVANT["Science"]))
        grades_str = "\n".join([
            f"  - {k.replace('_', ' ')}: {profile.get(k, 'C')}"
            for k in relevant_keys
        ])

        top3_str = "\n".join([
            f"  {i+1}. {item['career']} ({item['confidence_percent']}%)"
            for i, item in enumerate(xgb_result.get("top_3", []))
        ]) or f"  1. {effective_career} (primary)"

        prompt = f"""You are an expert career guidance counsellor for Nigerian secondary school students at SSS level.

=== STUDENT ACADEMIC PROFILE ===
- School Type: {profile.get('School_Type', 'Government School')}
- Department: {dept}
- Academic Strength: {profile.get('Academic_Strength', 'Average')}
- Best Subject Category: {profile.get('Best_Subject_Category', dept)}
- Subject Credits (C & above): {profile.get('WAEC_Credits', 5)} subjects

=== SUBJECT GRADES ===
{grades_str}

=== ASSESSMENT TEST SCORES ===
- Aptitude Test: {test_scores.get('aptitude_score_10', 5.0):.1f} / 10 (Logical & Numerical Reasoning)
- Cognitive Test: {test_scores.get('cognitive_score_10', 5.0):.1f} / 10 (Memory & Pattern Recognition)
- Psychometric Interest Score: {test_scores.get('psychometric_avg_5', 3.0):.2f} / 5 (RIASEC Career Interest Scale)
- Personality Score: {test_scores.get('sentiment_avg_5', 3.0):.2f} / 5 (Big Five Behavioural Traits)

=== AI MODEL RECOMMENDATION ===
- Primary Career Path: {effective_career}
- Model Confidence: {confidence:.1f}%
- Top 3 Predicted Paths:
{top3_str}

=== YOUR TASK ===
Write a detailed, personalised career recommendation report using exactly this structure:

### Career Pathway: {effective_career}
[2-3 sentences: Describe this career path in a Nigerian context. Mention specific industries or sectors.]

### \U0001f4ca Your Profile at a Glance
[Summarise the student's department, academic strength, and top grades in bullet points.]

### \U0001f4aa Key Strengths Detected
[4-6 bullet points referencing SPECIFIC grades and test scores.]

### \U0001f680 Actionable Next Steps
[Exactly 3 numbered steps. Include: (1) WAEC subject focus, (2) a Nigerian university or online resource, (3) a practical activity.]

### \U0001f393 JAMB Subject Combination
[List the recommended JAMB subjects for {effective_career} in Nigeria.]

IMPORTANT: Be warm, encouraging, and specific. Address the student as "you". Reference their actual grades and scores.
"""
        for model_name in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"]:
            try:
                if genai_client is not None:
                    response = genai_client.models.generate_content(model=model_name, contents=prompt)
                elif _genai_supports_generative_model and hasattr(genai, "GenerativeModel"):
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                else:
                    logger.warning("Google Generative AI library loaded, but no supported generation API is available.")
                    break
                text = getattr(response, "text", "") or ""
                if text.strip():
                    return {
                        "summary": _ensure_summary_career_alignment(text, effective_career),
                        "fallback_prediction": xgb_result,
                    }
            except Exception as exc:
                logger.warning("Gemini model %s failed: %s", model_name, exc)

    # Local fallback if Gemini fails or API key is not configured/revoked
    fallback_text = generate_local_fallback(xgb_result, test_scores, profile)
    return {
        "summary": fallback_text,
        "fallback_prediction": xgb_result,
        "is_fallback": True
    }


def recommend_with_gemini(student_profile, test_scores, student_id=None):
    xgb_result = predict_career(student_profile)
    xgb_result = align_prediction_with_department(xgb_result, student_profile)
    return gemini_final_prediction(xgb_result, test_scores, student_profile)
