"""
utils/data_processor.py
Clean, validate and normalize uploaded health CSV/Excel files.
"""

import pandas as pd
import numpy as np


# Accepted synonyms for required columns
COLUMN_ALIASES = {
    "HeartRate": ["heartrate", "heart_rate", "heart rate", "hr", "pulse", "bpm"],
    "Steps":     ["steps", "step_count", "stepcount", "daily_steps", "dailysteps"],
    "Gender":    ["gender", "sex", "g"],
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

    Returns
    -------
    df  : cleaned DataFrame with canonical column names
    log : list of processing steps taken
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
    log.append(f"Loaded {original_rows} rows from '{filepath.split('/')[-1]}'")

    # ── Normalize column names ─────────────────────────────────────────────────
    df, rename_log = _normalize_columns(df)
    log.extend(rename_log)

    # Strip whitespace from all column headers
    df.columns = [c.strip() for c in df.columns]

    # ── Validate required columns ──────────────────────────────────────────────
    _validate_required_columns(df)

    # ── Remove duplicates ─────────────────────────────────────────────────────
    before = len(df)
    df = df.drop_duplicates()
    dropped = before - len(df)
    if dropped:
        log.append(f"Removed {dropped} duplicate rows")

    # ── Handle missing values ─────────────────────────────────────────────────
    missing_counts = df[["HeartRate", "Steps", "Gender"]].isnull().sum()
    for col, cnt in missing_counts.items():
        if cnt == 0:
            continue
        if col in ("HeartRate", "Steps"):
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            log.append(f"Filled {cnt} missing '{col}' values with median ({median_val:.1f})")
        elif col == "Gender":
            df[col] = df[col].fillna("Unknown")
            log.append(f"Filled {cnt} missing 'Gender' values with 'Unknown'")

    # ── Coerce numeric types ───────────────────────────────────────────────────
    df["HeartRate"] = pd.to_numeric(df["HeartRate"], errors="coerce")
    df["Steps"]     = pd.to_numeric(df["Steps"],     errors="coerce")

    # Drop rows where coercion failed
    coerce_failed = df[["HeartRate", "Steps"]].isnull().any(axis=1).sum()
    if coerce_failed:
        df = df.dropna(subset=["HeartRate", "Steps"])
        log.append(f"Dropped {coerce_failed} rows with non-numeric HeartRate/Steps")

    # ── Remove physiologically impossible values ───────────────────────────────
    hr_outliers = ((df["HeartRate"] < 20) | (df["HeartRate"] > 300)).sum()
    if hr_outliers:
        df = df[(df["HeartRate"] >= 20) & (df["HeartRate"] <= 300)]
        log.append(f"Removed {hr_outliers} rows with impossible HeartRate values (<20 or >300)")

    step_outliers = (df["Steps"] < 0).sum()
    if step_outliers:
        df = df[df["Steps"] >= 0]
        log.append(f"Removed {step_outliers} rows with negative Steps")

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
