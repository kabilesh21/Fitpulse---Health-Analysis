"""
utils/data_processor.py
Clean, validate and normalize uploaded health CSV/Excel files.
"""

import os
import pandas as pd
import numpy as np


# Accepted synonyms for required columns and advanced health vitals
COLUMN_ALIASES = {
    "HeartRate":      ["heartrate", "heart_rate", "heart rate", "hr", "pulse", "bpm"],
    "Steps":          ["steps", "step_count", "stepcount", "daily_steps", "dailysteps"],
    "Gender":         ["gender", "sex", "g"],
    "SystolicBP":     ["systolic", "sys", "systolic_bp", "systolic bp", "sbp", "systolicbloodpressure"],
    "DiastolicBP":    ["diastolic", "dia", "diastolic_bp", "diastolic bp", "dbp", "diastolicbloodpressure"],
    "SpO2":           ["spo2", "oxygen", "ox", "o2", "saturation", "oxygen_saturation", "sp02"],
    "Temperature":    ["temperature", "temp", "bodytemp", "body_temp", "t"],
    "SleepDuration":  ["sleepduration", "sleep", "sleep_duration", "hours_sleep", "sleep_hours", "sleeptime"],
    "CaloriesBurned": ["calories", "caloriesburned", "calories_burned", "cal", "energy"],
    "StressLevel":    ["stress", "stresslevel", "stress_level", "stress_score"]
}


def _normalize_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Map known column aliases to canonical names."""
    log = []
    rename_map = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue  # already correct
        for alias in aliases:
            if alias in lower_cols:
                rename_map[lower_cols[alias]] = canonical
                log.append(f"Renamed column '{lower_cols[alias]}' → '{canonical}'")
                break

    if rename_map:
        df = df.rename(columns=rename_map)
    return df, log


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Raise ValueError if any required column is missing after normalization."""
    required = ["Gender", "Steps", "HeartRate"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}. "
            "Please ensure your file has Gender, Steps, and HeartRate columns."
        )


def process_health_data(filepath: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Load, clean, and validate health data from a CSV or Excel file.
    Fills advanced health metrics with clinical defaults if they are missing.
    """
    log = []

    # ── Load ──────────────────────────────────────────────────────────────────
    ext = filepath.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        df = pd.read_csv(filepath)
    elif ext in ("xlsx", "xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    original_rows = len(df)
    import re
    display_name = os.path.basename(filepath)
    display_name = re.sub(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}_', '', display_name)
    log.append(f"Loaded {original_rows} rows from '{display_name}'")

    # ── Normalize column names ─────────────────────────────────────────────────
    df, rename_log = _normalize_columns(df)
    log.extend(rename_log)

    # Strip whitespace from all column headers
    df.columns = [c.strip() for c in df.columns]

    # ── Validate required columns ──────────────────────────────────────────────
    _validate_required_columns(df)

    # ── Populate Advanced Vitals Defaults if missing ─────────────────────────
    advanced_defaults = {
        "SystolicBP": 120.0,
        "DiastolicBP": 80.0,
        "SpO2": 98.0,
        "Temperature": 36.6,
        "SleepDuration": 8.0,
        "CaloriesBurned": 2000.0,
        "StressLevel": 3.0
    }
    for col, default_val in advanced_defaults.items():
        if col not in df.columns:
            df[col] = default_val
            log.append(f"Missing '{col}', filled all rows with baseline default ({default_val})")

    # ── Remove duplicates ─────────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    if dropped:
        log.append(f"Removed {dropped} duplicate rows")

    # ── Coerce numeric types & Handle missing values ──────────────────────────
    numeric_cols = ["HeartRate", "Steps", "SystolicBP", "DiastolicBP", "SpO2", "Temperature", "SleepDuration", "CaloriesBurned", "StressLevel"]
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        missing_count = df[col].isnull().sum()
        if missing_count > 0:
            median_val = df[col].median()
            if pd.isnull(median_val):
                median_val = advanced_defaults.get(col, 72.0)
            df[col] = df[col].fillna(median_val)
            log.append(f"Filled {missing_count} missing '{col}' values with median ({median_val:.1f})")

    df["Gender"] = df["Gender"].fillna("Unknown")

    # Drop rows where coercion of critical columns failed
    coerce_failed = df[["HeartRate", "Steps"]].isnull().any(axis=1).sum()
    if coerce_failed:
        df = df.dropna(subset=["HeartRate", "Steps"])
        log.append(f"Dropped {coerce_failed} rows with non-numeric HeartRate/Steps")

    # ── Remove physiologically impossible values ───────────────────────────────
    impossible_bounds = [
        ("HeartRate", 20, 300),
        ("Steps", 0, 100000),
        ("SystolicBP", 50, 260),
        ("DiastolicBP", 30, 160),
        ("SpO2", 30, 100),
        ("Temperature", 25, 45),
        ("SleepDuration", 0, 24),
        ("CaloriesBurned", 0, 15000),
        ("StressLevel", 1, 10)
    ]
    for col, low, high in impossible_bounds:
        outliers = ((df[col] < low) | (df[col] > high)).sum()
        if outliers > 0:
            df = df[(df[col] >= low) & (df[col] <= high)]
            log.append(f"Removed {outliers} rows with outlier values in '{col}' (<{low} or >{high})")

    # ── Normalize Gender labels ────────────────────────────────────────────────
    df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
    df["Gender"] = df["Gender"].replace({
        "M": "Male", "F": "Female", "0": "Female", "1": "Male",
        "Woman": "Female", "Man": "Male",
    })

    # ── Heart Rate Classification ──────────────────────────────────────────────
    def classify_hr(hr):
        if hr < 60:   return "Low"
        if hr <= 100: return "Normal"
        return "High"

    df["HR_Category"] = df["HeartRate"].apply(classify_hr)

    final_rows = len(df)
    log.append(f"Final dataset: {final_rows} clean rows (removed {original_rows - final_rows} total)")

    return df.reset_index(drop=True), log
