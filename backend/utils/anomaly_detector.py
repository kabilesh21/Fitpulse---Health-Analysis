"""
utils/anomaly_detector.py
Detect health anomalies using Z-score, IQR, and Isolation Forest.
Calculates a 0-100 Health Risk Score and Explainable AI reasons.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def _zscore_flags(series: pd.Series, threshold: float = 2.5) -> pd.Series:
    """Return boolean Series: True where |z-score| > threshold."""
    mean, std = series.mean(), series.std()
    if std == 0:
        return pd.Series([False] * len(series), index=series.index)
    return ((series - mean).abs() / std) > threshold


def _iqr_flags(series: pd.Series, multiplier: float = 1.5) -> pd.Series:
    """Return boolean Series: True where value is outside IQR fences."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return (series < (q1 - multiplier * iqr)) | (series > (q3 + multiplier * iqr))


def _isolation_forest_flags(df: pd.DataFrame) -> pd.Series:
    """Return boolean Series using Isolation Forest on multiple vitals."""
    if len(df) < 2:
        return pd.Series([False] * len(df), index=df.index)
        
    features_to_use = ["HeartRate", "Steps", "SpO2", "Temperature", "SleepDuration", "StressLevel"]
    features = df[features_to_use].copy()
    
    for col in features_to_use:
        features[col] = pd.to_numeric(features[col], errors="coerce")
    defaults = {"HeartRate": 72.0, "Steps": 5000.0, "SpO2": 98.0, "Temperature": 36.6, "SleepDuration": 8.0, "StressLevel": 3.0}
    features = features.fillna(value=defaults)
    
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    # Use a small contamination to find extreme multivariate outliers
    model  = IsolationForest(contamination=0.06, random_state=42, n_estimators=100)
    preds  = model.fit_predict(X_scaled)   # -1 = anomaly
    return pd.Series(preds == -1, index=df.index)


def calculate_risk_and_explain(row) -> tuple[float, str, str]:
    """
    Calculate a Health Risk Score (0-100), Risk Level (Low/Med/High), 
    and an Explainable AI text explaining the anomalies.
    """
    penalties = []
    explanations = []

    hr = row.get("HeartRate", 72.0)
    spo2 = row.get("SpO2", 98.0)
    sys_bp = row.get("SystolicBP", 120.0)
    dia_bp = row.get("DiastolicBP", 80.0)
    temp = row.get("Temperature", 36.6)
    sleep = row.get("SleepDuration", 8.0)
    stress = row.get("StressLevel", 3.0)
    steps = row.get("Steps", 5000.0)

    # 1. Heart Rate
    if hr > 150 or hr < 40:
        penalties.append(35.0)
        explanations.append(f"Critical Heart Rate ({hr:.0f} bpm)")
    elif hr > 120 or hr < 50:
        penalties.append(20.0)
        explanations.append(f"Abnormal Heart Rate ({hr:.0f} bpm)")

    # 2. SpO2
    if spo2 < 90:
        penalties.append(45.0)
        explanations.append(f"Critically Low SpO2 ({spo2:.1f}%)")
    elif spo2 < 95:
        penalties.append(25.0)
        explanations.append(f"Low SpO2 ({spo2:.1f}%)")

    # 3. Blood Pressure
    if sys_bp > 140 or sys_bp < 85 or dia_bp > 90 or dia_bp < 55:
        penalties.append(25.0)
        explanations.append(f"Hypertension/Hypotension BP ({sys_bp:.0f}/{dia_bp:.0f} mmHg)")
    elif sys_bp > 130 or dia_bp > 85:
        penalties.append(10.0)
        explanations.append(f"Elevated BP ({sys_bp:.0f}/{dia_bp:.0f} mmHg)")

    # 4. Temperature
    if temp > 39.0 or temp < 35.0:
        penalties.append(25.0)
        explanations.append(f"High Fever/Hypothermia Temp ({temp:.1f}°C)")
    elif temp > 38.0 or temp < 35.8:
        penalties.append(15.0)
        explanations.append(f"Mild Fever/Low Temp ({temp:.1f}°C)")

    # 5. Sleep Duration
    if sleep < 5.0:
        penalties.append(20.0)
        explanations.append(f"Critical Sleep Deprivation ({sleep:.1f}h)")
    elif sleep < 6.5 or sleep > 10.5:
        penalties.append(10.0)
        explanations.append(f"Insufficient Sleep ({sleep:.1f}h)")

    # 6. Stress Level
    if stress >= 9.0:
        penalties.append(25.0)
        explanations.append(f"Extreme Stress Level ({stress:.0f}/10)")
    elif stress >= 7.0:
        penalties.append(15.0)
        explanations.append(f"High Stress Level ({stress:.0f}/10)")

    # 7. Physical Steps
    if steps < 1000:
        penalties.append(15.0)
        explanations.append(f"Extremely Sedentary Activity ({steps:.0f} steps)")
    elif steps < 3000:
        penalties.append(10.0)
        explanations.append(f"Low Daily Steps ({steps:.0f} steps)")

    risk_score = min(100.0, sum(penalties))
    
    if risk_score >= 60.0:
        risk_level = "High"
    elif risk_score >= 30.0:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    anomaly_reason = "; ".join(explanations) if explanations else "Normal Vitals"
    return risk_score, risk_level, anomaly_reason


def detect_anomalies(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Run three anomaly detection methods, combine results, 
    and calculate personal health scores and explainable AI reasons.
    """
    df = df.copy()
    
    # Coerce critical vital columns to numeric to handle any database legacy string values
    vitals = ["HeartRate", "Steps", "SpO2", "Temperature", "SleepDuration", "StressLevel", "SystolicBP", "DiastolicBP"]
    for col in vitals:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Method 1: Z-score on HeartRate ────────────────────────────────────────
    z_hr = _zscore_flags(df["HeartRate"], threshold=2.5)

    # ── Method 2: IQR on HeartRate ────────────────────────────────────────────
    iqr_hr = _iqr_flags(df["HeartRate"])

    # ── Method 3: Isolation Forest (multivariate) ─────────────────────────────
    iforest = _isolation_forest_flags(df)

    # ── Calculate Risk scores and XAI tags for each row ───────────────────────
    scores = []
    levels = []
    reasons = []
    
    for i in range(len(df)):
        score, level, reason = calculate_risk_and_explain(df.iloc[i])
        scores.append(score)
        levels.append(level)
        reasons.append(reason)

    df["Risk_Score"] = scores
    df["Risk_Level"] = levels
    
    # ── Anomaly Vote ──────────────────────────────────────────────────────────
    # Flag as anomaly if consensus vote is met, clinical alert is present, or risk is High
    vote_score = z_hr.astype(int) + iqr_hr.astype(int) + iforest.astype(int)
    is_anomaly = (vote_score >= 2) | (df["Risk_Level"] == "High") | (df["HeartRate"] > 150) | (df["HeartRate"] < 40) | (df["SpO2"] < 90)

    df["Anomaly"] = is_anomaly.map({True: "Yes", False: "No"})
    df["Anomaly_Score"] = vote_score

    # Merge explainable reasons
    final_reasons = []
    for i in range(len(df)):
        r = reasons[i]
        # Append statistical tags if flagged
        stats_flags = []
        if vote_score.iloc[i] >= 2:
            stats_flags.append("Statistical consensus anomaly")
        elif iforest.iloc[i]:
            stats_flags.append("Multivariate outlier pattern")
            
        if stats_flags:
            if r == "Normal Vitals":
                r = ", ".join(stats_flags)
            else:
                r = r + " (" + ", ".join(stats_flags) + ")"
        final_reasons.append(r)

    df["Anomaly_Reason"] = final_reasons

    # ── Stats ──────────────────────────────────────────────────────────────────
    anomaly_df = df[df["Anomaly"] == "Yes"]
    total      = len(df)
    n_anom     = len(anomaly_df)

    anomaly_stats = {
        "total":             total,
        "anomaly_count":     n_anom,
        "normal_count":      total - n_anom,
        "anomaly_pct":       round(n_anom / total * 100, 2) if total else 0,
        "methods_used":      ["Z-score", "IQR", "Isolation Forest"],
        "z_score_flags":     int(z_hr.sum()),
        "iqr_flags":         int(iqr_hr.sum()),
        "iforest_flags":     int(iforest.sum()),
        "clinical_flags":    int((df["HeartRate"] > 150).sum() + (df["HeartRate"] < 40).sum() + (df["SpO2"] < 90).sum()),
        "avg_anomaly_hr":    round(anomaly_df["HeartRate"].mean(), 1) if n_anom else 0,
        "max_anomaly_hr":    round(anomaly_df["HeartRate"].max(), 1) if n_anom else 0,
        "min_anomaly_hr":    round(anomaly_df["HeartRate"].min(), 1) if n_anom else 0,
    }

    return df, anomaly_stats

