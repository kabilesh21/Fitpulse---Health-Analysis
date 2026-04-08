"""
utils/report_generator.py
Generate detailed health insight reports and PDF exports.
"""

import os
import statistics
from datetime import datetime


def generate_report(records: list, anomaly_stats: dict, processing_log: list) -> dict:
    """Build a comprehensive health report dictionary."""

    heart_rates = [r["HeartRate"] for r in records if r.get("HeartRate") is not None]
    steps_list  = [r["Steps"]     for r in records if r.get("Steps")     is not None]
    anomalies   = [r for r in records if r.get("Anomaly") == "Yes"]

    avg_hr  = round(statistics.mean(heart_rates), 1) if heart_rates else 0
    std_hr  = round(statistics.stdev(heart_rates), 2) if len(heart_rates) > 1 else 0
    avg_st  = round(statistics.mean(steps_list),   1) if steps_list else 0

    # ── Health insights ────────────────────────────────────────────────────────
    insights = []

    if avg_hr > 90:
        insights.append({
            "type":    "warning",
            "title":   "Elevated Average Heart Rate",
            "detail":  f"Average heart rate of {avg_hr} bpm is above the ideal resting range (60–80 bpm). "
                       "Consider stress management, hydration, and cardiovascular evaluation.",
        })
    elif avg_hr < 55:
        insights.append({
            "type":    "info",
            "title":   "Low Average Heart Rate",
            "detail":  f"Average heart rate of {avg_hr} bpm is below 60 bpm. "
                       "This may be normal in athletes but warrants evaluation if symptomatic.",
        })
    else:
        insights.append({
            "type":    "success",
            "title":   "Heart Rate in Healthy Range",
            "detail":  f"Average heart rate of {avg_hr} bpm is within the normal resting range (60–100 bpm).",
        })

    if anomaly_stats.get("anomaly_pct", 0) > 10:
        insights.append({
            "type":    "danger",
            "title":   "High Anomaly Rate Detected",
            "detail":  f"{anomaly_stats['anomaly_pct']}% of records show anomalous patterns. "
                       "A comprehensive cardiovascular review is recommended.",
        })
    elif anomaly_stats.get("anomaly_pct", 0) > 5:
        insights.append({
            "type":    "warning",
            "title":   "Moderate Anomaly Rate",
            "detail":  f"{anomaly_stats['anomaly_pct']}% anomaly rate detected. Monitor closely.",
        })
    else:
        insights.append({
            "type":    "success",
            "title":   "Low Anomaly Rate",
            "detail":  f"Only {anomaly_stats.get('anomaly_pct', 0)}% anomalies detected — healthy profile.",
        })

    if avg_st < 5000:
        insights.append({
            "type":    "warning",
            "title":   "Low Physical Activity",
            "detail":  f"Average {avg_st:.0f} steps/day is below the recommended 7,500–10,000 steps. "
                       "Increasing activity may improve cardiovascular health.",
        })
    elif avg_st >= 10000:
        insights.append({
            "type":    "success",
            "title":   "Excellent Activity Level",
            "detail":  f"Average {avg_st:.0f} steps/day exceeds the 10,000-step goal.",
        })

    # ── Recommendations ────────────────────────────────────────────────────────
    recommendations = [
        {"icon": "🏃", "title": "Regular Cardiovascular Exercise",
         "detail": "Aim for 150 min/week of moderate aerobic activity to maintain healthy heart rate."},
        {"icon": "💧", "title": "Stay Hydrated",
         "detail": "Dehydration can elevate heart rate by 7–8 bpm. Drink 2–3 L water daily."},
        {"icon": "😴", "title": "Prioritize Sleep",
         "detail": "7–9 hours of quality sleep helps regulate resting heart rate."},
        {"icon": "🧘", "title": "Stress Management",
         "detail": "Chronic stress elevates baseline heart rate. Practice mindfulness or yoga."},
        {"icon": "🩺", "title": "Regular Health Checkups",
         "detail": "Annual ECG and blood pressure checks are recommended for heart health monitoring."},
    ]

    if anomaly_stats.get("anomaly_count", 0) > 0:
        recommendations.insert(0, {
            "icon":   "⚠️",
            "title":  "Consult a Healthcare Provider",
            "detail": f"{anomaly_stats['anomaly_count']} anomalies detected. "
                      "Please consult a physician for a proper clinical evaluation.",
        })

    # ── Statistics table ───────────────────────────────────────────────────────
    low_count    = sum(1 for r in records if r.get("HR_Category") == "Low")
    normal_count = sum(1 for r in records if r.get("HR_Category") == "Normal")
    high_count   = sum(1 for r in records if r.get("HR_Category") == "High")

    top_anomalies = sorted(anomalies, key=lambda r: abs(r["HeartRate"] - avg_hr), reverse=True)[:10]

    return {
        "generated_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "statistics": {
            "total_records":  len(records),
            "avg_heart_rate": avg_hr,
            "max_heart_rate": max(heart_rates) if heart_rates else 0,
            "min_heart_rate": min(heart_rates) if heart_rates else 0,
            "std_heart_rate": std_hr,
            "avg_steps":      avg_st,
            "max_steps":      max(steps_list) if steps_list else 0,
            "hr_low_count":   low_count,
            "hr_normal_count":normal_count,
            "hr_high_count":  high_count,
        },
        "anomaly_stats":      anomaly_stats,
        "insights":           insights,
        "recommendations":    recommendations,
        "top_anomalies":      top_anomalies,
        "processing_log":     processing_log,
    }


def generate_pdf_report(report: dict, filename: str) -> str:
    """Generate a PDF report using reportlab. Returns path to PDF file."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        out_path = "/tmp/fitpulse_report.pdf"
        doc      = SimpleDocTemplate(out_path, pagesize=A4,
                                     leftMargin=2*cm, rightMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
        styles   = getSampleStyleSheet()
        story    = []

        BLUE  = colors.HexColor("#0ea5e9")
        DARK  = colors.HexColor("#0f172a")
        GRAY  = colors.HexColor("#64748b")
        GREEN = colors.HexColor("#22c55e")
        RED   = colors.HexColor("#ef4444")

        title_style = ParagraphStyle("Title", parent=styles["Title"],
                                     textColor=BLUE, fontSize=24, spaceAfter=4)
        h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                     textColor=DARK, fontSize=14, spaceBefore=16, spaceAfter=6)
        body_style  = ParagraphStyle("Body", parent=styles["Normal"],
                                     textColor=GRAY, fontSize=10, leading=14)

        story.append(Paragraph("FitPulse Health Anomaly Report", title_style))
        story.append(Paragraph(f"Generated: {report['generated_at']} | File: {filename}", body_style))
        story.append(HRFlowable(width="100%", color=BLUE, thickness=1, spaceAfter=12))

        # Stats table
        story.append(Paragraph("Summary Statistics", h2_style))
        s = report["statistics"]
        a = report["anomaly_stats"]
        stat_data = [
            ["Metric", "Value"],
            ["Total Records",        str(s["total_records"])],
            ["Average Heart Rate",   f"{s['avg_heart_rate']} bpm"],
            ["Max Heart Rate",       f"{s['max_heart_rate']} bpm"],
            ["Min Heart Rate",       f"{s['min_heart_rate']} bpm"],
            ["Std Deviation (HR)",   f"{s['std_heart_rate']} bpm"],
            ["Average Steps",        f"{s['avg_steps']:.0f}"],
            ["Anomalies Detected",   str(a["anomaly_count"])],
            ["Anomaly Rate",         f"{a['anomaly_pct']}%"],
        ]
        tbl = Table(stat_data, colWidths=[9*cm, 7*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f9ff")]),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING",      (0,0), (-1,-1), 6),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 0.4*cm))

        # Insights
        story.append(Paragraph("Health Insights", h2_style))
        for ins in report["insights"]:
            story.append(Paragraph(f"<b>{ins['title']}</b>", body_style))
            story.append(Paragraph(ins["detail"], body_style))
            story.append(Spacer(1, 0.2*cm))

        # Recommendations
        story.append(Paragraph("Recommendations", h2_style))
        for rec in report["recommendations"]:
            story.append(Paragraph(f"<b>{rec['title']}</b>: {rec['detail']}", body_style))
            story.append(Spacer(1, 0.15*cm))

        doc.build(story)
        return out_path

    except ImportError:
        # Fallback: plain text file if reportlab not installed
        out_path = "/tmp/fitpulse_report.txt"
        with open(out_path, "w") as f:
            f.write("FitPulse Health Anomaly Report\n")
            f.write(f"Generated: {report['generated_at']}\n\n")
            s = report["statistics"]
            f.write(f"Total Records:     {s['total_records']}\n")
            f.write(f"Avg Heart Rate:    {s['avg_heart_rate']} bpm\n")
            f.write(f"Anomalies:         {report['anomaly_stats']['anomaly_count']}\n")
            f.write(f"Anomaly Rate:      {report['anomaly_stats']['anomaly_pct']}%\n\n")
            f.write("INSIGHTS\n")
            for i in report["insights"]:
                f.write(f"- {i['title']}: {i['detail']}\n")
        return out_path
