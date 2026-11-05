def display(*args, **kwargs):
    for a in args:
        print(a)

def forceTheme(*args, **kwargs):
    pass


# --- CELL ---

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold, RandomizedSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, ConfusionMatrixDisplay
from sklearn.utils.class_weight import compute_sample_weight

from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

import joblib


def prepare_feature_frame(df_input, feature_names, categorical_features, numerical_features):
    df_proc = df_input.copy()
    df_proc.columns = [str(c).strip().lower().replace(" ", "_").replace("__", "_") for c in df_proc.columns]
    df_proc = df_proc.rename(columns={"igbo_/_hausa": "igbo_hausa"})

    normalized_feature_names = [str(c).strip().lower().replace(" ", "_").replace("__", "_") for c in feature_names]
    normalized_categorical = [str(c).strip().lower().replace(" ", "_").replace("__", "_") for c in categorical_features]
    normalized_numerical = [str(c).strip().lower().replace(" ", "_").replace("__", "_") for c in numerical_features]

    for col in normalized_categorical:
        if col in df_proc.columns:
            df_proc[col] = df_proc[col].fillna("Unknown")
            df_proc[col] = df_proc[col].astype(str).replace({"0": "Unknown", "0.0": "Unknown", "nan": "Unknown", "None": "Unknown"})
        else:
            df_proc[col] = "Unknown"

    for col in normalized_numerical:
        if col in df_proc.columns:
            series_value = df_proc[col].squeeze()
            if isinstance(series_value, pd.DataFrame):
                series_value = series_value.iloc[:, 0]
            df_proc[col] = pd.to_numeric(series_value, errors="coerce")
            df_proc[col] = df_proc[col].fillna(0.0)
        else:
            df_proc[col] = 0.0

    for col in normalized_feature_names:
        if col not in df_proc.columns:
            df_proc[col] = 0.0 if col in normalized_numerical else "Unknown"

    return df_proc.loc[:, normalized_feature_names].copy()

# --- CELL ---

repo_root = Path.cwd()
if (repo_root / "backend" / "ml_models" / "training" / "new_model.ipynb").exists():
    data_path = repo_root / "data" / "combined_career_dataset.xlsx"
else:
    data_path = repo_root / ".." / "data" / "combined_career_dataset.xlsx"

print(f"Using data file: {data_path}")
repo_root = Path.cwd()

search_dirs = [repo_root] + list(repo_root.parents[:4])
data_path = None
for base in search_dirs:
    candidate = base / "data" / "combined_career_dataset.xlsx"
    if candidate.exists():
        data_path = candidate
        break

if data_path is None:
    raise FileNotFoundError(
        "Unable to locate combined_career_dataset.xlsx. Tried:\n" +
        "\n".join(str(base / "data" / "combined_career_dataset.xlsx") for base in search_dirs)
    )

print(f"Using data file: {data_path}")
data = pd.read_excel(data_path)

df = pd.DataFrame(data)
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_colwidth', None)

# --- CELL ---

df = df.copy()
df = df.loc[:, ~df.columns.duplicated()].copy()
df = df.reset_index(drop=True)
df = df.fillna(0)
df = df.rename(columns=lambda x: x.removesuffix('_waec'))

# Drop empty (0) values in Career Path, Class Departments, School Type, intended career path, Universty Level, Academic Strength, Best Subject Category, Current Career Satisfaction
cols_to_clean = ['career_path', 'department', 'school_type', 'intended_career_path', 'university_level', 'academic_strength', 'best_subject_category', 'current_career_satisfaction']
df[cols_to_clean] = df[cols_to_clean].replace(0, np.nan)
df['jamb_score'] = df['jamb_score'].replace("I don't remember ", 0)

# Keep the row but fill missing career labels using the intended career path when possible.
df['career_path'] = df['career_path'].replace({0: np.nan, '': np.nan, '0': np.nan})
df['career_path'] = df['career_path'].fillna(df['intended_career_path'])
df['career_path'] = df['career_path'].replace({0: np.nan, '': np.nan, '0': np.nan})

# Drop rows that still have no career label after imputation.
df = df.dropna(subset=['career_path'])

# Drop Age column
df = df.drop(columns=['age', 'name'])

# Clean CGPA column
def clean_cgpa(value):
    if pd.isna(value) or value is None:
        return np.nan
    val = str(value).strip().lower()
    refuse_keywords = [
        "rather not", "don't remember", "i don't", "none", 
        "nil", "n/a", "na", "not sure", "prefer not"
    ]
    if any(kw in val for kw in refuse_keywords) or val in ["", "none", "nil"]:
        return np.nan
    if "/" in val:
        parts = val.split("/")
        try:
            numerator = float(re.sub(r"[^\d.]", "", parts[0]))
            return round(numerator, 2)
        except:
            return np.nan
    val = val.replace(":", ".")
    cleaned = re.sub(r"[^\d.]", "", val)
    if cleaned.count(".") > 1 or cleaned == "" or cleaned == ".":
        return np.nan
    try:
        num = float(cleaned)
        if 0 <= num <= 5.0:
            return round(num, 2)
        elif 5 < num <= 100:          
            return round(num / 20, 2) 
        else:
            return np.nan
    except:
        return np.nan
# Apply cleaning
df["cgpa"] = df["cgpa"].apply(clean_cgpa)

# Convert WAEC to int
df['waec_year'] = df['waec_year'].astype(int)
df['waec_credits'] = df['waec_credits'].astype(int)
df['jamb_score'] = df['jamb_score'].astype(int)

print(f"Shape of dataset: rows={df.shape[0]}, columns={df.shape[1]}")
print("\nDistribution of Labels (target variables):")
print(df['career_path'].value_counts())
print("\nDistribution of Class Departments:")
print(df['department'].value_counts())
print("\nDistribution of school type:")
print(df['school_type'].value_counts())
print("\nMissing Values:")
print(df.isnull().sum())
print("\nRows with missing career path after cleaning:", df['career_path'].isna().sum())
print("\nThe Dataset after cleaning:")
display(df.head(10))


# --- CELL ---

# Career Paths Analysis
career_path_analysis = df.groupby(['intended_career_path', 'career_path'], observed=True).agg('size')
display(career_path_analysis)
plt.figure(figsize=(18, 10))
plt.subplot(2, 2, 1)

# Distribution of Career path
sns.countplot(y="career_path", data=df, hue="department", palette="magma")
for container in plt.gca().containers:
    plt.bar_label(container, fontsize=12)
plt.title("DIstribution of Career Path")
plt.ylabel("Career Path")

# Distribution of departments
plt.subplot(2, 2, 2)
sns.countplot(x="department", data=df, hue="school_type", palette="magma")
plt.title("Distribution of Department")
for container in plt.gca().containers:
    plt.bar_label(container, fontsize=12)
plt.xlabel("Departments")
plt.legend(title="School Type", loc="lower right")

# Distribution of Age
plt.subplot(2, 2, 3)
sns.countplot(x="university_level", data=df, palette='rocket', hue='department')
for container in plt.gca().containers:
    plt.bar_label(container, fontsize=12)
plt.title("Distribution of University Level")
plt.xlabel("University Level")

# Distribution of Acadmic Strenght
plt.subplot(2, 2, 4)
sns.countplot(x="academic_strength", data=df, hue="department", palette="viridis")
plt.title("Distribution of Academic Strenght")
for container in plt.gca().containers:
    plt.bar_label(container, fontsize=12)
plt.xlabel("Academic Strenght")

plt.tight_layout()
plt.show()


# --- CELL ---

# Distribution of other features
plt.figure(figsize=(10, 6))

# JAMB
sns.histplot(df['jamb_score'].dropna(), bins=30, kde=True)
plt.title("Distribution of JAMB Score")
plt.xlabel("JAMB Score")

plt.tight_layout()
plt.show()

# --- CELL ---

subjects_cols = ["mathematics", "english", "civic_education", "physics", "chemistry", "biology", "further_mathematics", "agricultural_science", "geography", "technical_drawing", "computer_studies", "yoruba", "igbo_hausa", "data_processing",
                 "literature_in_english", "christian_religious_studies_islamic_studies", "creative_arts", "economics", "financial_accounting", "commerce", "government", "marketing", "french", "intended_career_path"]
categorical_columns = ["gender", "school_type", "department", "academic_strength", "best_subject_category", "current_career_satisfaction", "career_influence"] + subjects_cols
numerical_columns = ["waec_year", "waec_credits", "cgpa", "jamb_score"]

# Ensure preprocessor uses the normalized column names (underscores) to match X_train
cat_cols_norm = [c.lower().strip().replace(' ', '_').replace('__', '_') for c in categorical_columns]
num_cols_norm = [c.lower().strip().replace(' ', '_').replace('__', '_') for c in numerical_columns]
for col in cat_cols_norm:
    if col in df.columns:
        df[col] = df[col].replace({0: 'Unknown', 0.0: 'Unknown', np.nan: 'Unknown'}).astype(str)
for col in num_cols_norm:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

preprocessor = ColumnTransformer(transformers=[
    ('num', StandardScaler(), num_cols_norm),
    ('cat', OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), cat_cols_norm)
])
features = cat_cols_norm + num_cols_norm
display(preprocessor)

# --- CELL ---

label_encoder = LabelEncoder()


X = df[features].copy()
y = df["career_path"].dropna()
y_encoded = label_encoder.fit_transform(y)

print("First 5 rows of X (Features):")
display(X.head())
print("\nDistribution of y (target):")
print(y.value_counts())
print("\nUnique classes in target variable:", label_encoder.classes_)

print("\nClass imbalance summary:")
for i, (class_label, count) in enumerate(zip(label_encoder.classes_, y.value_counts())):
    print(f"  {class_label}: {count}")

# --- CELL ---

X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, shuffle=True, stratify=y_encoded)
print(f"\nTrain size: {X_train.shape[0]} | Test size: {X_test.shape[0]}")
print("Class balance in train:")
for i, (class_label, count) in enumerate(zip(label_encoder.classes_, np.unique(y_train, return_counts=True)[1])):
    print(f"  {class_label}: {count}")
print("\nClass balance in test:")
for i, (class_label, count) in enumerate(zip(label_encoder.classes_, np.unique(y_test, return_counts=True)[1])):
    print(f"  {class_label}: {count}")


# --- CELL ---

rf_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(
        n_estimators=300,
        max_depth=18,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=1
    ))
])

# Fit the model
rf_model.fit(X_train, y_train)

# Evaluation
rf_train_accuracy = accuracy_score(y_train, rf_model.predict(X_train))
rf_test_accuracy = accuracy_score(y_test, rf_model.predict(X_test))
print(f"Random Forest Train Accuracy: {rf_train_accuracy*100:.2f}%")
print(f"Random Forest Test Accuracy: {rf_test_accuracy*100:.2f}%")

# Classification Report
rf_target_names = [str(c) if not (isinstance(c, float) and np.isnan(c)) else "Unknown" for c in label_encoder.classes_]
rf_classification_report = classification_report(y_test, rf_model.predict(X_test), target_names=rf_target_names, zero_division=0)
print("\nClassification Report for Random Forest Model:")
print(rf_classification_report)

# --- CELL ---

rf_classification_report_dict = classification_report(y_test, rf_model.predict(X_test), target_names=label_encoder.classes_, output_dict=True, zero_division=0)

# Plot Random Forest Classification Report
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(pd.DataFrame(rf_classification_report_dict).iloc[:-1, :].T, annot=True, cmap="Blues", cbar=False, ax=ax)
ax.set_title("Random Forest Classification Report", fontsize=16)
#plt.savefig("ml/models/classification_report.png", dpi=120, bbox_inches="tight")
plt.show()

# --- CELL ---

xgb_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', XGBClassifier(n_estimators=400,
    max_depth=8,
    learning_rate=0.01,
    subsample=0.85,
    colsample_bytree=0.80,
    use_label_encoder=False,
    eval_metric="mlogloss",
    random_state=42,
    n_jobs=1,
    verbosity=0))
])

sample_weights = compute_sample_weight(class_weight='balanced', y=y_train)
xgb_model.fit(X_train, y_train, classifier__sample_weight=sample_weights)

# Evaluation
xgb_train_accuracy = accuracy_score(y_train, xgb_model.predict(X_train))
xgb_test_accuracy = accuracy_score(y_test, xgb_model.predict(X_test))
print(f"XGBoost Train Accuracy: {xgb_train_accuracy*100:.2f}%")
print(f"XGBoost Test Accuracy: {xgb_test_accuracy*100:.2f}%")

# Classification Report
xgb_classification_report = classification_report(y_test, xgb_model.predict(X_test), target_names=label_encoder.classes_, zero_division=0)
print("\nXGBoost Classification Report:")
print(xgb_classification_report)

# --- CELL ---

xgb_classification_report_dict = classification_report(y_test, xgb_model.predict(X_test), target_names=label_encoder.classes_, output_dict=True, zero_division=0)
# Plot Random Forest Classification Report
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(pd.DataFrame(xgb_classification_report_dict).iloc[:-1, :].T, annot=True, cmap="Blues", cbar=False, ax=ax)
ax.set_title("XGBoost Classification Report", fontsize=16)
#plt.savefig("ml/models/classification_report.png", dpi=120, bbox_inches="tight")
plt.show()

# --- CELL ---

param_distributions = {
    'classifier__n_estimators': [100, 200, 300, 500],
    'classifier__learning_rate': [0.01, 0.1, 0.2, 0.3],
    'classifier__max_depth': [3, 5, 7, 9],
    'classifier__min_child_weight': [1, 3, 5, 7],
    'classifier__gamma': [0, 0.1, 0.2, 0.3],
    'classifier__subsample': [0.6, 0.8, 1.0],
    'classifier__colsample_bytree': [0.6, 0.8, 1.0]
}

xgb_random_search = RandomizedSearchCV(
    estimator=xgb_model,
    param_distributions=param_distributions,
    n_iter=20,
    cv=5,
    scoring='accuracy',
    random_state=42,
    n_jobs=1
)

# Fit to data
xgb_random_search.fit(X_train, y_train)

# Access results
print(f"Best Parameters: {xgb_random_search.best_params_}")
print(f"Best CV Score: {xgb_random_search.best_score_:.4f}")
print(f"Best Estimator: {xgb_random_search.best_estimator_}")

# Fit best model
xgb_best_model = xgb_random_search.best_estimator_

# Predict on validation and test set
xgb_best_model_pred = xgb_best_model.predict(X_test)
xgb_best_test_accuracy = (xgb_best_model_pred == y_test).mean()
print(f"Test accuracy of tuned XGBoost: {xgb_best_test_accuracy*100:.2f}%")
print(f"Train Accuracy of Tuned XGBoost: {accuracy_score(y_train, xgb_best_model.predict(X_train))*100:.2f}%")
print(f"Accuracy Score for Xgboost before tuning: {xgb_test_accuracy}")
print(f"Model Improvement: {(xgb_best_test_accuracy - xgb_test_accuracy)*100:.2f}%")

# --- CELL ---

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

rf_cv  = cross_val_score(rf_model, X, y_encoded, cv=cv, scoring="accuracy", n_jobs=1)
xgb_cv = cross_val_score(xgb_best_model, X, y_encoded, cv=cv, scoring="accuracy", n_jobs=1)

print(f"Random Forest  CV: {rf_cv.mean()*100:.2f}% ± {rf_cv.std()*100:.2f}%")
print(f"XGBoost Tuned  CV: {xgb_cv.mean()*100:.2f}% ± {xgb_cv.std()*100:.2f}%")

# --- CELL ---

fig, ax = plt.subplots(figsize=(12, 9))
cm = confusion_matrix(y_test, xgb_best_model.predict(X_test))
disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                               display_labels=[c[:20] for c in label_encoder.classes_])
disp.plot(ax=ax, xticks_rotation=45, colorbar=False, cmap="Blues")
ax.set_title("XGBoost — Confusion Matrix (Test Set)", fontsize=14)
plt.tight_layout()
# plt.savefig("ml/models/confusion_matrix.png", dpi=120, bbox_inches="tight")
plt.show()


# --- CELL ---

xgb_best_classification_report_dict = classification_report(y_test, xgb_best_model.predict(X_test), target_names=label_encoder.classes_, output_dict=True, zero_division=0)
# Plot Random Forest Classification Report
fig, ax = plt.subplots(figsize=(12, 10))
sns.heatmap(pd.DataFrame(xgb_best_classification_report_dict).iloc[:-1, :].T, annot=True, cmap="Blues", cbar=False, ax=ax)
ax.set_title("XGBoost Best Model Classification Report", fontsize=16)
#plt.savefig("ml/models/classification_report.png", dpi=120, bbox_inches="tight")
plt.show()

# --- CELL ---

feature_importance = pd.DataFrame({
    'Features': features,
    'Importances': xgb_best_model.named_steps['classifier'].feature_importances_
}).sort_values(by='Importances', ascending=False).reset_index(drop=True)
print('Top 20 Feature Importances from XGBOost Tuned Model:')
display(feature_importance.head(20))

#Plotting XGBoost Tuned Model Feature Importance
plt.figure(figsize=(13, 8))
sns.barplot(x='Importances', y='Features', data=feature_importance, hue='Features', palette='magma', errorbar=None, legend=False)
for container in plt.gca().containers:
    plt.bar_label(container, fmt='%.1f', label_type='edge', padding=3)
plt.title('XGBoost Tuned Model Feature Importance')
plt.xlabel('Importances')
plt.ylabel('Features')
plt.tight_layout()
plt.show()

# --- CELL ---

import joblib
from pathlib import Path

# Resolve the correct models directory regardless of the notebook working directory
ROOT_DIR = Path.cwd().resolve()
while ROOT_DIR.parent != ROOT_DIR:
    if (ROOT_DIR / "backend" / "model_artifacts").exists() or (ROOT_DIR / "backend" / "ml_models").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

model_dir = ROOT_DIR / "backend" / "model_artifacts"
model_dir.mkdir(parents=True, exist_ok=True)

model_path = model_dir / "xgb_best_model.pkl"
encoder_path = model_dir / "label_encoder.pkl"

joblib.dump(xgb_best_model, model_path)
joblib.dump(label_encoder, encoder_path)

print("Saved model artifacts to:")
print(f"  - {model_path}")
print(f"  - {encoder_path}")

expected = [model_path, encoder_path]
print("Model file checklist:")
for f in expected:
    size = f.stat().st_size if f.exists() else 0
    status = f"✅  {size/1024:.1f} KB" if f.exists() else "❌  MISSING"
    print(f"  {status}  {f}")

# --- CELL ---

# Prepare a sample student record using the shared preprocessing function
sample = {
    'Gender': 'Male',
    'School_Type': 'Mission / Faith School',
    'Department': 'Science',
    'Mathematics': 'A',
    'English': 'A',
    'Civic Education': 'D',
    'Physics': 'E',
    'Chemistry': 'A',
    'Biology': 'A',
    'Agricultural Science': 'B',
    'Geography': 'D',
    'Academic_Strength': 'Low',
    'Best_Subject_Category': 'Science',
    'current_career_satisfaction': 'Not very confident',
    'Career_Influence': 'Personal passion'
}

df_sample = pd.DataFrame([sample])

# Add missing columns with sensible defaults
all_expected_cols = [
    'Gender', 'School_Type', 'Department', 'Academic_Strength', 'Best_Subject_Category',
    'Mathematics', 'English', 'Civic Education', 'Physics', 'Chemistry', 'Biology',
    'Further Mathematics', 'Agricultural Science', 'Geography', 'Technical Drawing',
    'Computer Studies', 'Yoruba', 'Igbo / Hausa', 'Data Processing', 'Literature In English',
    'History', 'Christian Religious Studies/Islamic Studies', 'French', 'Creative Arts',
    'Economics', 'Financial Accounting', 'Commerce', 'Government', 'Marketing', 'current_career_satisfaction', 'Career_Influence'
]

for col in all_expected_cols:
    if col not in df_sample.columns:
        df_sample[col] = 'Unknown'

# Grade mapping for all grade columns
grade_map = {'A':8, 'B':6, 'C':5, 'D':3, 'E':2, 'F':1, 'Unknown':5}
grade_cols = [col for col in all_expected_cols if col not in ['Gender','School_Type','Department',
              'Academic_Strength','Best_Subject_Category','current_career_satisfaction','Career_Influence']]

for col in grade_cols:
    if col in df_sample.columns:
        df_sample[col] = df_sample[col].astype(str).str.upper().map(grade_map).fillna(5)

# Use shared preprocessing function for consistent schema handling
sample_frame = df_sample.copy()
sample_frame.columns = [str(c).strip().lower().replace(" ", "_").replace("__", "_") for c in sample_frame.columns]
sample_frame = sample_frame.rename(columns={"igbo_/_hausa": "igbo_hausa"})
df_sample = prepare_feature_frame(sample_frame, features, categorical_columns, numerical_columns)

if sample["Mathematics"] == "F" or sample["English"] == "F":
    print("\nWarning: The student has failed in Mathematics or English. Career recommendations may not be accurate.")
    predicted_career = "None, please improve your grades in Mathematics and English to get career recommendations."
    proba = [0] * len(label_encoder.classes_)
else:
    pred_encoded = xgb_best_model.predict(df_sample)[0]
    proba = xgb_best_model.predict_proba(df_sample)[0]
    predicted_career = label_encoder.inverse_transform([pred_encoded])[0]

print("\n=== SS Student Career Prediction ===")
print(f"**Predicted Career:** {predicted_career}")
print(f"Confidence: {max(proba)*100:.1f}%")

print("\nTop 3:")
for c, p in sorted(zip(label_encoder.classes_, proba), key=lambda x: x[1], reverse=True)[:3]:
    print(f"  • {c} ({p*100:.1f}%)")
