"""
utils/ml_compare.py
Trains and compares multiple machine learning models (Random Forest, Decision Tree, Logistic Regression, Isolation Forest)
on the user's vitals dataset to display comparative analytics.
"""

import time
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score

def compare_models(records: list) -> dict:
    """
    Train and compare Random Forest, Decision Tree, Logistic Regression, and Isolation Forest.
    Returns comparison metrics.
    """
    if len(records) < 10:
        return {
            "error": "At least 10 health records are required to perform Machine Learning comparison.",
            "models": {}
        }

    df = pd.DataFrame(records)
    
    # Fill defaults for any missing columns
    for col in ["heart_rate", "steps", "spo2", "temperature", "sleep_duration", "stress_level", "anomaly"]:
        if col not in df.columns:
            if col == "anomaly":
                df[col] = "No"
            elif col == "spo2":
                df[col] = 98.0
            elif col == "temperature":
                df[col] = 36.6
            elif col == "sleep_duration":
                df[col] = 8.0
            elif col == "stress_level":
                df[col] = 3.0
            else:
                df[col] = 0.0

    # Features and Target
    feature_cols = ["heart_rate", "steps", "spo2", "temperature", "sleep_duration", "stress_level"]
    X = df[feature_cols].copy()
    y = df["anomaly"].apply(lambda x: 1 if str(x).strip().lower() == "yes" or x is True else 0)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split for supervised models evaluation (use stratify if classes permit)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.3, random_state=42, stratify=y
        )
    except ValueError:
        # Fallback if classes are too unbalanced
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.3, random_state=42
        )

    results = {}

    # ── 1. Random Forest ──────────────────────────────────────────────────────
    t0 = time.time()
    rf = RandomForestClassifier(n_estimators=50, random_state=42)
    rf.fit(X_train, y_train)
    t_rf = time.time() - t0
    
    y_pred_rf = rf.predict(X_test)
    acc_rf = accuracy_score(y_test, y_pred_rf)
    anom_count_rf = int((rf.predict(X_scaled) == 1).sum())

    results["Random Forest"] = {
        "name": "Random Forest",
        "type": "Supervised Ensemble",
        "train_time": round(t_rf * 1000, 2), # ms
        "accuracy": round(acc_rf * 100, 1),
        "anomalies_detected": anom_count_rf,
        "parameters": "n_estimators=50, max_depth=None",
        "description": "Ensemble classifier using bootstrapped decision trees. Highly robust and handles noise well."
    }

    # ── 2. Decision Tree ──────────────────────────────────────────────────────
    t0 = time.time()
    dt = DecisionTreeClassifier(random_state=42, max_depth=5)
    dt.fit(X_train, y_train)
    t_dt = time.time() - t0
    
    y_pred_dt = dt.predict(X_test)
    acc_dt = accuracy_score(y_test, y_pred_dt)
    anom_count_dt = int((dt.predict(X_scaled) == 1).sum())

    results["Decision Tree"] = {
        "name": "Decision Tree",
        "type": "Supervised Tree",
        "train_time": round(t_dt * 1000, 2),
        "accuracy": round(acc_dt * 100, 1),
        "anomalies_detected": anom_count_dt,
        "parameters": "max_depth=5, criterion=gini",
        "description": "Splits dataset by informative features. Prone to overfitting but highly explainable."
    }

    # ── 3. Logistic Regression ────────────────────────────────────────────────
    t0 = time.time()
    lr = LogisticRegression(random_state=42, max_iter=200)
    lr.fit(X_train, y_train)
    t_lr = time.time() - t0
    
    y_pred_lr = lr.predict(X_test)
    acc_lr = accuracy_score(y_test, y_pred_lr)
    anom_count_lr = int((lr.predict(X_scaled) == 1).sum())

    results["Logistic Regression"] = {
        "name": "Logistic Regression",
        "type": "Supervised Linear",
        "train_time": round(t_lr * 1000, 2),
        "accuracy": round(acc_lr * 100, 1),
        "anomalies_detected": anom_count_lr,
        "parameters": "solver=lbfgs, C=1.0",
        "description": "Linear classifier that models anomaly probability. Fast, stable, and works well for linearly separable data."
    }

    # ── 4. Isolation Forest ───────────────────────────────────────────────────
    t0 = time.time()
    # Unsupervised: fits on all scaled data
    contamination = max(0.01, min(0.20, y.mean())) if y.mean() > 0 else 0.05
    iforest = IsolationForest(contamination=contamination, random_state=42, n_estimators=50)
    iforest.fit(X_scaled)
    t_if = time.time() - t0
    
    # -1 represents anomaly in sklearn IsolationForest
    y_pred_if = iforest.predict(X_scaled)
    y_pred_if_binary = np.where(y_pred_if == -1, 1, 0)
    acc_if = accuracy_score(y, y_pred_if_binary)
    anom_count_if = int((y_pred_if_binary == 1).sum())

    results["Isolation Forest"] = {
        "name": "Isolation Forest",
        "type": "Unsupervised Tree",
        "train_time": round(t_if * 1000, 2),
        "accuracy": round(acc_if * 100, 1),
        "anomalies_detected": anom_count_if,
        "parameters": f"contamination={contamination:.2f}, n_estimators=50",
        "description": "Isolates anomalies rather than profiling normal data points. Excellent for high-dimensional outlier detection."
    }

    # Feature Importance (using Random Forest)
    importances = rf.feature_importances_
    feature_importance_list = [
        {"feature": feat, "importance": round(imp * 100, 1)}
        for feat, imp in zip(["Heart Rate", "Steps", "SpO2", "Temperature", "Sleep Duration", "Stress Level"], importances)
    ]
    feature_importance_list = sorted(feature_importance_list, key=lambda x: x["importance"], reverse=True)

    return {
        "models": results,
        "feature_importances": feature_importance_list
    }
