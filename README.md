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

## 🚀 Quickstart Guide

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
