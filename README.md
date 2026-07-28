# Strataform Clinical Labs — Vitals & Anomaly Diagnostics

Strataform is a web-based clinical vital analysis, dataset cleaning, and cardiac health anomaly detection system. It provides patients and physicians with automated clinical processing pipelines, interactive data visualization, real-time AI assistance, and professional audit reports.

---

## 🎯 Platform Purpose
Strataform allows users to upload, audit, clean, and visualize wearable vital records (heart rate, blood pressure, oxygen saturation, temperature, steps, sleep, and stress). It automatically highlights physiological irregularities (such as tachycardia, hypertensive spikes, fever, and hypoxemia) using statistical outlier algorithms (Clinical Boundaries, Z-Score, Interquartile Range, and Isolation Forest ML models) to deliver immediate remedies, clinical alerts, and downloadable audit trail reports.

---

## 📂 File Directory Structure

```text
Fitpulse---Health-Analysis-main/
│
├── backend/                             # Python Flask Web Backend
│   ├── app.py                           # Core application endpoints, routing, and controllers
│   ├── fitpulse.db                      # Local SQLite database storing patients & logs
│   ├── requirements.txt                 # Backend dependency list (Flask, Pandas, ReportLab, etc.)
│   ├── runproject.bat                   # Shell script to build venv & launch application
│   └── utils/
│       ├── __init__.py
│       ├── anomaly_detector.py          # Clinical rules, Z-Score, and IQR anomaly filters
│       ├── data_processor.py            # CSV dataset parser, sanitizer, and column mapper
│       ├── db.py                        # SQLite seeder, schemas, and user credentials manager
│       ├── ml_compare.py                # Machine learning isolation forest pipelines
│       └── report_generator.py          # ReportLab PDF compiled report rendering
│
├── frontend/                            # Client-Side Assets & Templates
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css                 # Main website styles (Glassmorphism & animations)
│   │   ├── img/
│   │   │   └── logo.jpg                 # Strataform clinical company logo
│   │   └── js/
│   │       └── main.js                  # Dynamic UI updates, API calls, and modals
│   └── templates/
│       ├── base.html                    # Root HTML layout containing header & modals
│       ├── index.html                   # Platform landing page & admission portal options
│       ├── login.html                   # Patient login/signup and Physician Console forms
│       ├── upload.html                  # CSV dataset drag-drop & manual vitals entry forms
│       ├── dashboard.html               # Real-time vital metrics dashboard & KPI grid
│       ├── report.html                  # Clinical insights, alerts, and remedies report page
│       ├── doctor_dashboard.html        # Physician view showing patient registry & login logs
│       ├── services.html                # Listing of diagnostics clinic specialties
│       └── about.html                   # Medical staff credentials & virtual care team
│
├── fitpulse_vitals_sample.csv           # Reference wearable vitals template for upload
└── README.md                            # Comprehensive user and developer guide
```

---

## 🛠️ Options & Features Available

### 1. Patient Access Portal
* **Register/Sign Up**: Patients can create an account by filling out their username, age, gender, and clinical checkup purpose.
  * **"Other" Checkup Option**: If the patient's purpose is not listed in the options, selecting "Other..." displays a text field to specify their custom purpose.
* **Interactive Profile Editing**: Patients can click their username badge in the top-right corner to open a profile modal, letting them update their name, age, gender, and purpose dynamically without requiring pictures.
* **Automatic Dataset Protection**: The system automatically prompts active patient sessions to wipe temporary clinical logs on reload or logout to keep medical records private.

### 2. Clinical Admission Desk (Uploads)
* **CSV Wearable Log Import**: Supports drag-and-drop or browsing of CSV files mapping vital records over time.
* **Manual Vital Entry**: Provides a manual entry form to type in heart rate, blood pressure, oxygen levels, sleep duration, daily steps, and temperature to test vitals instantly.

### 3. Real-Time Vitals Dashboard
* **Dynamic KPIs**: Displays clinical averages and counts:
  - Vitals Average (Heart Rate, SpO2, Temperature)
  - Daily Averages (Sleep, Steps, Calories)
  - Current Cardiovascular Risk (Low/Medium/High)
  - Flagged Outlier Anomalies
* **Interactive Charts**: Interactive Line charts mapping heart rate over time, blood pressure ranges, and step/sleep correlations.
* **Clean & Filter**: Allows patients to remove clinical outliers with Z-score or IQR bounds to clean up their database logs.

### 4. Interactive Medical Reports
* **Clinical Summaries**: Compiles average vitals, outlier distribution, and diagnostic insights.
* **Dynamic PDF Export**: Allows patients to print or download a professional A4 diagnostic report with clinical letterheads, signature blocks, and contact watermarks.
* **Severe Causes Alerts & Instant Remedies (Web-Only)**: Dynamically checks vital thresholds (e.g., Tachycardia, Hypoxemia, Hypertension) to suggest causes and instant home remedies. This advice is displayed **only on the webpage** and is excluded from printed PDF documents.
* **Supervised AI Assistant**: A floating AI health chatbot is available at the bottom-right corner to explain vital ranges and clinical terms.

### 5. Physician Console Dashboard
* **Patient Registry**: Doctors (Dr. Albert & Dr. Suganya) can view all registered patient demographics, vital records counts, and cardiovascular risk statuses.
* **Admission Checklist**: A checklist manager to track admitting, logging, analyzing, and discharging stages.
* **Login History Audit Trail**: Chronological day-by-day logs tracking patient sign-ins.
* **Downloadable Portal Access Reports**: Generates a professional tabular access audit sheet that is downloaded directly as an HTML report for internal clinical security reviews.
