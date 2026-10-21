# Web-Based ML Model Evaluator

A lightweight web application for uploading tabular datasets (CSV), configuring supervised machine learning models, training them on the fly, and evaluating performance metrics through interactive visualizations.

---

## 🏛️ Architecture Overview

The repository is modularly structured into dedicated frontend, backend, machine learning, and database components:

```
Web-Based-ML-model-evaluator/
├── backend/                        # Python Flask application
│   ├── app.py                     # Main application factory & health check
│   ├── config.py                  # Environment & database configuration
│   ├── requirements.txt           # Python dependencies
│   ├── database/                  # SQLAlchemy ORM database initialization
│   │   ├── __init__.py
│   │   └── db.py
│   ├── models/                    # Relational data models
│   │   ├── __init__.py
│   │   ├── user.py                # User accounts & authentication
│   │   ├── dataset.py             # Dataset metadata & column tracking
│   │   └── evaluation.py          # Trained model runs & evaluation metrics
│   ├── ml/                        # Machine Learning core module
│   │   ├── __init__.py
│   │   ├── preprocessor.py        # Missing values, encoding, scaling & split
│   │   ├── trainer.py             # Scikit-learn algorithm training
│   │   └── evaluator.py           # Metrics calculation & confusion matrix
│   ├── routes/                    # REST API Blueprints
│   │   ├── __init__.py
│   │   ├── auth_routes.py         # /api/auth (register, login, logout)
│   │   ├── dataset_routes.py      # /api/dataset (upload, preview, metadata)
│   │   └── ml_routes.py           # /api/ml (algorithms, train, evaluations)
│   ├── uploads/                   # Stored uploaded CSV files
│   └── saved_models/              # Serialized trained model files (.joblib)
├── frontend/                      # Web user interface
│   ├── index.html                 # Single-page web dashboard
│   ├── css/
│   │   └── style.css              # Custom responsive styles
│   └── js/
│       └── app.js                 # REST API client & dynamic UI renderer
├── documents/                     # Project SRS, UML diagrams, test plans
├── .gitignore                     # Git ignore rules for Python, virtualenv, and data
└── README.md
```

---

## �️ Database Schema

The application uses SQLAlchemy ORM with SQLite (configurable to PostgreSQL/MySQL) and consists of four relational tables:

### Entity-Relationship Diagram

```
┌─────────────────────┐
│       users         │
├─────────────────────┤
│ id (PK)            │◄────┐
│ username (unique)   │     │
│ email (unique)      │     │
│ password_hash       │     │
│ created_at          │     │
└─────────────────────┘     │
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         │                  │                  │
┌────────▼────────┐  ┌──────▼──────────┐  ┌───▼─────────────────┐
│    datasets     │  │     models      │  │ evaluation_results  │
├─────────────────┤  ├─────────────────┤  ├─────────────────────┤
│ id (PK)        │◄─┤ id (PK)        │◄─┤ id (PK)            │
│ user_id (FK)   │  │ user_id (FK)   │  │ user_id (FK) ⚠️    │
│ filename        │  │ dataset_id (FK)│  │ model_id (FK)      │
│ file_path       │  │ model_name      │  │ metrics_json       │
│ file_size       │  │ algorithm       │  │ confusion_matrix   │
│ row_count       │  │ model_path      │  │ report_json        │
│ column_count    │  │ status          │  │ created_at         │
│ metadata_json   │  │ config_json     │  └────────────────────┘
│ created_at      │  │ created_at      │
└─────────────────┘  └─────────────────┘
```

### Table Descriptions

#### **1. users**
Stores user account information with authentication credentials.

| Column         | Type          | Constraints           | Description                    |
|----------------|---------------|-----------------------|--------------------------------|
| id             | Integer       | Primary Key           | Unique user identifier         |
| username       | String(80)    | Unique, Not Null      | User's display name            |
| email          | String(120)   | Unique, Not Null      | User's email address           |
| password_hash  | String(256)   | Not Null              | Bcrypt-hashed password         |
| created_at     | DateTime      | Not Null, Default NOW | Account creation timestamp     |

**Relationships**: One-to-many with `datasets`, `models`, and `evaluation_results`

---

#### **2. datasets**
Stores uploaded CSV dataset metadata and file references.

| Column         | Type          | Constraints           | Description                    |
|----------------|---------------|-----------------------|--------------------------------|
| id             | Integer       | Primary Key           | Unique dataset identifier      |
| user_id        | Integer       | Foreign Key, Not Null | Owner reference → users.id     |
| filename       | String(255)   | Not Null              | Original uploaded filename     |
| file_path      | String(512)   | Not Null              | Server storage path            |
| file_size      | BigInteger    | Nullable              | File size in bytes             |
| row_count      | Integer       | Nullable              | Number of data rows            |
| column_count   | Integer       | Nullable              | Number of columns              |
| metadata_json  | JSON          | Nullable              | Column names, types, stats     |
| created_at     | DateTime      | Not Null, Default NOW | Upload timestamp               |

**Relationships**: Belongs to `User`, has many `MLModel`

---

#### **3. models**
Stores trained machine learning model configurations and serialized file paths.

| Column         | Type          | Constraints           | Description                    |
|----------------|---------------|-----------------------|--------------------------------|
| id             | Integer       | Primary Key           | Unique model identifier        |
| user_id        | Integer       | Foreign Key, Not Null | Owner reference → users.id     |
| dataset_id     | Integer       | Foreign Key, Not Null | Source dataset → datasets.id   |
| model_name     | String(128)   | Not Null              | User-defined model name        |
| algorithm      | String(128)   | Not Null              | Algorithm (e.g., random_forest)|
| model_path     | String(512)   | Nullable              | Path to .joblib serialized file|
| status         | String(32)    | Not Null, Default: pending | Training status           |
| config_json    | JSON          | Nullable              | Hyperparameters, split ratio   |
| created_at     | DateTime      | Not Null, Default NOW | Model creation timestamp       |

**Relationships**: Belongs to `User` and `Dataset`, has many `EvaluationResult`

---

#### **4. evaluation_results**
Stores model performance metrics, confusion matrices, and classification reports.

| Column                | Type          | Constraints           | Description                    |
|-----------------------|---------------|-----------------------|--------------------------------|
| id                    | Integer       | Primary Key           | Unique evaluation identifier   |
| user_id               | Integer       | Foreign Key, Not Null | Owner reference → users.id ⚠️ |
| model_id              | Integer       | Foreign Key, Not Null | Evaluated model → models.id    |
| metrics_json          | JSON          | Not Null              | Accuracy, F1, MSE, RMSE, R²    |
| confusion_matrix_json | JSON          | Nullable              | Confusion matrix array         |
| report_json           | JSON          | Nullable              | Per-class precision/recall     |
| created_at            | DateTime      | Not Null, Default NOW | Evaluation timestamp           |

**Relationships**: Belongs to `User` and `MLModel`

---

### 🔒 Schema Integrity: Owner Consistency Constraint

**Design Decision**:
- The `evaluation_results` table stores both `user_id` and `model_id` as foreign keys.
- While `user_id` could technically be derived from `models.user_id`, storing it directly enables:
  - Faster queries when filtering evaluations by user without joining through models
  - Clearer audit trails showing who created each evaluation
  - Support for potential future features (e.g., shared model evaluations)

**Integrity Protection**:
To prevent data inconsistency where an evaluation's `user_id` doesn't match its model's owner, a **database-level CHECK constraint** has been implemented:

```sql
ALTER TABLE evaluation_results 
ADD CONSTRAINT evaluation_owner_matches_model_owner 
CHECK (user_id = (SELECT user_id FROM models WHERE models.id = model_id));
```

**Implementation** (in `models/evaluation.py`):
```python
__table_args__ = (
    CheckConstraint(
        """
        user_id = (SELECT user_id FROM models WHERE models.id = model_id)
        """,
        name="evaluation_owner_matches_model_owner"
    ),
)
```

**What This Prevents**:
```python
# ✅ Valid: User 1 creates evaluation for their own model
model = MLModel(user_id=1, dataset_id=5, algorithm="random_forest")
evaluation = EvaluationResult(user_id=1, model_id=model.id, metrics={...})

# ❌ BLOCKED: User 2 cannot create evaluation with mismatched owner
evaluation = EvaluationResult(user_id=2, model_id=model.id, metrics={...})
# Raises: IntegrityError - evaluation_owner_matches_model_owner constraint failed
```

**Result**: The database now enforces referential integrity, ensuring evaluation ownership always matches model ownership.

---

## �🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+ (Python 3.13 supported)
- Modern Web Browser (Chrome, Firefox, Edge)

### 2. Setup & Installation

Navigate to the `backend/` directory:
```bash
cd backend
```

Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r requirements.txt
```

### 3. Running the Application

Launch the Flask backend server:
```bash
python app.py
```

The application will start on:
👉 **http://127.0.0.1:5000**

Opening **http://127.0.0.1:5000** in your browser will automatically serve the full web interface!

---

## 📡 Core REST APIs

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | `GET` | Service health check |
| `/api/auth/register` | `POST` | Register user account |
| `/api/auth/login` | `POST` | User login session |
| `/api/dataset/upload` | `POST` | Upload CSV dataset & inspect columns |
| `/api/dataset/<id>/preview` | `GET` | Preview dataset top rows and statistics |
| `/api/ml/algorithms` | `GET` | List supported ML algorithms |
| `/api/ml/train` | `POST` | Train model, evaluate metrics, and save model |
| `/api/ml/evaluations/<user_id>` | `GET` | List evaluation history for user |

---

## 🤖 Supported ML Algorithms

- **Classification**:
  - Logistic Regression
  - Random Forest Classifier
  - Decision Tree Classifier
  - K-Nearest Neighbors (KNN)
- **Regression**:
  - Linear Regression
  - Random Forest Regressor
  - Decision Tree Regressor
  - KNN Regressor
