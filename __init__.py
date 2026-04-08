"""
utils/anomaly_detector.py
Detect health anomalies using Z-score, IQR, and Isolation Forest.
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
    """Return boolean Series using Isolation Forest on HeartRate + Steps."""
    features = df[["HeartRate", "Steps"]].copy()
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    model  = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    preds  = model.fit_predict(X_scaled)   # -1 = anomaly
    return pd.Series(preds == -1, index=df.index)


def detect_anomalies(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Run three anomaly detection methods and combine results.

    Anomaly column: "Yes" if flagged by ≥2 methods OR if heart rate
    is clinically critical (>150 or <40 bpm).

    Returns
    -------
    df           : DataFrame with 'Anomaly', 'Anomaly_Score', 'Anomaly_Reason' columns
    anomaly_stats: summary dict
    """
    df = df.copy()

    # ── Method 1: Z-score on HeartRate ────────────────────────────────────────
    z_hr    = _zscore_flags(df["HeartRate"], threshold=2.5)
    z_steps = _zscore_flags(df["Steps"],     threshold=2.5)

    # ── Method 2: IQR on HeartRate ────────────────────────────────────────────
    iqr_hr = _iqr_flags(df["HeartRate"])

    # ── Method 3: Isolation Forest (multivariate) ─────────────────────────────
    iforest = _isolation_forest_flags(df)

    # ── Vote: anomaly if ≥2 of 3 methods agree, or clinically extreme ─────────
    vote_score  = z_hr.astype(int) + iqr_hr.astype(int) + iforest.astype(int)
    clinical    = (df["HeartRate"] > 150) | (df["HeartRate"] < 40)
    is_anomaly  = (vote_score >= 2) | clinical

    df["Anomaly"]       = is_anomaly.map({True: "Yes", False: "No"})
    df["Anomaly_Score"] = vote_score  # 0–3

    # ── Reason tag ────────────────────────────────────────────────────────────
    def reason_tag(row):
        reasons = []
        idx = row.name
        if clinical.iloc[idx] if hasattr(clinical, 'iloc') else False:
            reasons.append("Clinical extreme HR")
        if z_hr.iloc[idx]:
            reasons.append("Z-score HR outlier")
        if iqr_hr.iloc[idx]:
            reasons.append("IQR HR outlier")
        if iforest.iloc[idx]:
            reasons.append("Multivariate outlier")
        return "; ".join(reasons) if reasons else "—"

    df = df.reset_index(drop=True)
    clinical_arr  = clinical.values
    z_hr_arr      = z_hr.values
    iqr_hr_arr    = iqr_hr.values
    iforest_arr   = iforest.values

    reasons = []
    for i in range(len(df)):
        r = []
        if clinical_arr[i]:  r.append("Clinical extreme HR")
        if z_hr_arr[i]:      r.append("Z-score HR outlier")
        if iqr_hr_arr[i]:    r.append("IQR HR outlier")
        if iforest_arr[i]:   r.append("Multivariate outlier")
        reasons.append("; ".join(r) if r else "—")
    df["Anomaly_Reason"] = reasons

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
        "clinical_flags":    int(clinical.sum()),
        "avg_anomaly_hr":    round(anomaly_df["HeartRate"].mean(), 1) if n_anom else 0,
        "max_anomaly_hr":    round(anomaly_df["HeartRate"].max(), 1) if n_anom else 0,
        "min_anomaly_hr":    round(anomaly_df["HeartRate"].min(), 1) if n_anom else 0,
    }

    return df, anomaly_stats
