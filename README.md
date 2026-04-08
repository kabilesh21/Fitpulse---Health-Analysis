# FitPulse-Health-Anomaly-Detection
📘 FitPulse Health Anomaly Detection

A Python-based data analysis project completed as part of the Infosys Springboard Virtual Internship: Python Programming.

🧠 Project Overview

FitPulse Health Anomaly Detection is a data analysis project that uses fitness device data (heart rate, pulse rate, steps, gender, age group) to:

Read and process Excel data

Perform data cleaning and preprocessing

Detect missing values

Convert values to numeric formats

Calculate gender-based statistics

Generate visualizations (Matplotlib / Plotly)

Build an interactive Streamlit Web App

Display meaningful insights and detect anomalies

This project demonstrates practical use of Python libraries for real-world data analysis.

📂 Project Structure
FitPulse-Health-Anomaly-Detection/
│
├── 1_read_excel.py
├── 2_null_check.py
├── 3_clean_data.py
├── 4_gender_analysis.py
├── 5_heart_status.py
├── 6_average_heart_rate.py
├── 7_plot_graphs.py
├── streamlit_app.py
├── Fitpulse_data.xlsx
│
├── outputs/
│     ├── output_screenshots.pdf  OR individual images
│
└── README.md

🔧 Technologies & Libraries Used

Python

Pandas (data processing)

NumPy (numerical operations)

Matplotlib (visualizations)

Plotly (interactive plots)

Scikit-learn (optional ML models)

Streamlit (web app interface)

OpenPyXL (Excel reading engine)

📊 Features & Tasks Performed
✔ 1. Read Excel dataset

Loaded Fitpulse_data.xlsx using pandas.

✔ 2. Check null values

Used data.isnull().sum()

Identified missing values.

✔ 3. Clean and preprocess data

Converted heartbeat, steps, pulse rate to numeric

Replaced invalid values

Removed NaN values

✔ 4. Gender-based analysis

Standardized gender column

Calculated average heart rate by gender

✔ 5. Visualizations

Created:

Line charts

Scatter plots

Gender comparison charts

Interactive Plotly graphs

✔ 6. Streamlit Web App

An interactive app built using:

streamlit run streamlit_app.py


Features in Streamlit:

Display dataset

Show average heart rate by gender

Generate graphs

Show health insights

▶️ How to Run the Project
1️⃣ Install dependencies
pip install pandas numpy matplotlib plotly streamlit scikit-learn openpyxl

2️⃣ Run Python scripts

Example:

python 1_read_excel.py
python 2_null_check.py

📁 Dataset Description

Fitpulse_data.xlsx contains:

Customer_ID

Age_Group

Gender

Heart Beat per Minute

Pulse Rate

Steps Count

This data is used for visualization and anomaly detection.

🖼 Outputs

All project outputs (terminal outputs, charts, Streamlit screenshots) are included in:

/outputs


or inside a single PDF file:

FitPulse_Output_Screenshots.pdf
