"""
utils/report_generator.py
Generate detailed health insight reports, baseline deviation analysis, early warning systems, and PDF exports.
"""

import os
import uuid
import tempfile
import statistics
from datetime import datetime

def generate_report(records: list, anomaly_stats: dict, processing_log: list) -> dict:
    """Build a comprehensive health report dictionary including baseline deviations and early warnings."""

    # Extrapolate keys based on DB column naming
    heart_rates = [r.get("heart_rate") or r.get("HeartRate") for r in records if (r.get("heart_rate") or r.get("HeartRate")) is not None]
    steps_list  = [r.get("steps") or r.get("Steps") for r in records if (r.get("steps") or r.get("Steps")) is not None]
    spo2_list   = [r.get("spo2") or r.get("SpO2") for r in records if (r.get("spo2") or r.get("SpO2")) is not None]
    sleep_list  = [r.get("sleep_duration") or r.get("SleepDuration") for r in records if (r.get("sleep_duration") or r.get("SleepDuration")) is not None]
    stress_list = [r.get("stress_level") or r.get("StressLevel") for r in records if (r.get("stress_level") or r.get("StressLevel")) is not None]
    temp_list   = [r.get("temperature") or r.get("Temperature") for r in records if (r.get("temperature") or r.get("Temperature")) is not None]
    sys_list    = [r.get("systolic_bp") or r.get("SystolicBP") for r in records if (r.get("systolic_bp") or r.get("SystolicBP")) is not None]
    dia_list    = [r.get("diastolic_bp") or r.get("DiastolicBP") for r in records if (r.get("diastolic_bp") or r.get("DiastolicBP")) is not None]
    risk_scores = [r.get("risk_score") or r.get("Risk_Score") or 0.0 for r in records]

    anomalies   = [r for r in records if r.get("anomaly") == "Yes" or r.get("Anomaly") == "Yes"]

    avg_hr  = round(statistics.mean(heart_rates), 1) if heart_rates else 72.0
    std_hr  = round(statistics.stdev(heart_rates), 2) if len(heart_rates) > 1 else 0.0
    avg_st  = round(statistics.mean(steps_list), 1) if steps_list else 5000.0
    avg_sp  = round(statistics.mean(spo2_list), 1) if spo2_list else 98.0
    avg_sl  = round(statistics.mean(sleep_list), 1) if sleep_list else 8.0
    avg_str = round(statistics.mean(stress_list), 1) if stress_list else 3.0
    avg_tmp = round(statistics.mean(temp_list), 1) if temp_list else 36.6
    avg_sys = round(statistics.mean(sys_list), 1) if sys_list else 120.0
    avg_dia = round(statistics.mean(dia_list), 1) if dia_list else 80.0

    # Calculate latest record
    latest = records[-1] if records else {}
    latest_hr = latest.get("heart_rate") or latest.get("HeartRate") or 72.0
    latest_sp = latest.get("spo2") or latest.get("SpO2") or 98.0
    latest_sl = latest.get("sleep_duration") or latest.get("SleepDuration") or 8.0
    latest_str = latest.get("stress_level") or latest.get("StressLevel") or 3.0
    latest_risk = latest.get("risk_score") or latest.get("Risk_Score") or 0.0
    latest_anomaly = latest.get("anomaly") or latest.get("Anomaly") or "No"

    insights = []

    # ── 1. Baseline Deviation Check ──────────────────────────────────────────
    # If the user has more than 5 logs, we evaluate deviation of the latest entry
    if len(records) >= 3:
        baseline_alerts = []
        
        # Heart rate deviation (> 15% from average)
        if abs(latest_hr - avg_hr) / avg_hr > 0.15:
            direction = "elevated" if latest_hr > avg_hr else "decreased"
            baseline_alerts.append(f"Heart Rate is {direction} ({latest_hr:.0f} vs average {avg_hr:.0f} bpm)")
            
        # SpO2 deviation (drop of >= 3% from average)
        if avg_sp - latest_sp >= 3.0:
            baseline_alerts.append(f"Oxygen Saturation dropped ({latest_sp:.1f}% vs average {avg_sp:.1f}%)")
            
        # Sleep duration deviation (short sleep >= 2 hours compared to baseline)
        if avg_sl - latest_sl >= 2.0:
            baseline_alerts.append(f"Sleep is short ({latest_sl:.1f}h vs average {avg_sl:.1f}h)")

        if baseline_alerts:
            insights.append({
                "type": "warning",
                "title": "Baseline Deviations Detected ⚠️",
                "detail": f"Your latest vital readings show unusual changes compared to your baseline averages: {', '.join(baseline_alerts)}."
            })
        else:
            insights.append({
                "type": "success",
                "title": "Baseline Normal 🟢",
                "detail": "Your latest vitals match your personal average baseline parameters closely."
            })

    # ── 2. Early Warning Alert Check ──────────────────────────────────────────
    # If risk scores are consecutively rising over the last 3 logs
    if len(risk_scores) >= 3:
        last_three = risk_scores[-3:]
        if last_three[0] < last_three[1] < last_three[2] and last_three[2] > 20:
            insights.append({
                "type": "danger",
                "title": "Health Warning Alert 🚨",
                "detail": "Warning: Your health risk score has increased consecutively over your last three entries (Risk scores: "
                          f"{last_three[0]:.0f} → {last_three[1]:.0f} → {last_three[2]:.0f}). Please monitor your symptoms."
            })
        elif last_three[2] >= 60.0:
            insights.append({
                "type": "danger",
                "title": "High Health Risk Warning 🛑",
                "detail": f"Your latest calculated risk score is critically high ({last_three[2]:.0f}/100). Consider resting and seeking clinical feedback."
            })

    # ── 3. Core Insights ───────────────────────────────────────────────────────
    if avg_hr > 90:
        insights.append({
            "type":    "warning",
            "title":   "Elevated Baseline Heart Rate",
            "detail":  f"Your average heart rate of {avg_hr} bpm is high. Try to monitor stress and caffeine intake.",
        })
    elif avg_hr < 55:
        insights.append({
            "type":    "info",
            "title":   "Low Baseline Heart Rate",
            "detail":  f"Your average heart rate of {avg_hr} bpm is low. Normal in athletes, but check if associated with dizziness.",
        })
    else:
        insights.append({
            "type":    "success",
            "title":   "Healthy Resting Heart Rate",
            "detail":  f"Your average heart rate of {avg_hr} bpm is in the healthy resting range.",
        })

    if avg_sp < 95:
        insights.append({
            "type":    "danger",
            "title":   "Mild Oxygen Desaturation (SpO2)",
            "detail":  f"Average oxygen saturation ({avg_sp}%) is below the healthy threshold of 95%. Monitor breathing.",
        })

    if avg_sl < 6.5:
        insights.append({
            "type":    "warning",
            "title":   "Inadequate Sleep Profile",
            "detail":  f"Average sleep duration ({avg_sl} hours) is below the recommended 7–9 hours. Focus on sleep hygiene.",
        })

    if avg_str >= 6.5:
        insights.append({
            "type":    "warning",
            "title":   "High Average Stress Level",
            "detail":  f"Average stress score is elevated ({avg_str}/10). Practice relaxation exercises.",
        })

    # ── Recommendations ────────────────────────────────────────────────────────
    recommendations = [
        {"icon": "🏃", "title": "Maintain Daily Activity",
         "detail": f"Your steps average is {avg_st:.0f}/day. Try to maintain at least 7,500 steps to support heart health."},
        {"icon": "💧", "title": "Adequate Hydration",
         "detail": "Dehydration elevates resting heart rate. Drink 2.5–3 liters of water daily."},
        {"icon": "😴", "title": "Consistent Sleep Schedule",
         "detail": "Aim for 7.5 to 8.5 hours of sleep at regular hours to regulate baseline blood pressure."},
        {"icon": "🧘", "title": "Stress Mitigation",
         "detail": "Incorporate 10-15 minutes of deep breathing or meditation to keep stress scores low."},
    ]

    if latest_anomaly == "Yes" or latest_risk >= 40:
        recommendations.insert(0, {
            "icon":   "🩺",
            "title":  "Consult a Medical Practitioner",
            "detail": f"Latest anomaly check is positive with a risk score of {latest_risk:.0f}/100. "
                      "Consider reviewing these metrics with a physician."
        })

    # ── Statistics mapping ─────────────────────────────────────────────────────
    low_count    = sum(1 for r in records if (r.get("HR_Category") or r.get("hr_category")) == "Low")
    normal_count = sum(1 for r in records if (r.get("HR_Category") or r.get("hr_category")) == "Normal" or (r.get("HR_Category") is None and 60 <= (r.get("HeartRate") or r.get("heart_rate", 72)) <= 100))
    high_count   = sum(1 for r in records if (r.get("HR_Category") or r.get("hr_category")) == "High")

    top_anomalies = sorted(anomalies, key=lambda r: r.get("risk_score") or r.get("Risk_Score") or 0.0, reverse=True)[:10]

    return {
        "generated_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "statistics": {
            "total_records":  len(records),
            "avg_heart_rate": avg_hr,
            "max_heart_rate": max(heart_rates) if heart_rates else 0.0,
            "min_heart_rate": min(heart_rates) if heart_rates else 0.0,
            "std_heart_rate": std_hr,
            "avg_steps":      avg_st,
            "max_steps":      max(steps_list) if steps_list else 0.0,
            "avg_spo2":       avg_sp,
            "avg_sleep":      avg_sl,
            "avg_stress":     avg_str,
            "avg_temp":       avg_tmp,
            "avg_systolic":   avg_sys,
            "avg_diastolic":  avg_dia,
            "hr_low_count":   low_count,
            "hr_normal_count":normal_count,
            "hr_high_count":  high_count,
            "latest_risk":    latest_risk,
            "latest_anomaly": latest_anomaly,
        },
        "anomaly_stats":      anomaly_stats,
        "insights":           insights,
        "recommendations":    recommendations,
        "top_anomalies":      top_anomalies,
        "processing_log":     processing_log,
    }


def generate_pdf_report(report: dict, filename: str, records: list = None) -> str:
    """Generate a professional tabular PDF report using reportlab. Returns path to PDF file."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.barcharts import VerticalBarChart

        selected_doctor = "Dr. K. Albert"
        if records and len(records) > 0:
            selected_doctor = records[-1].get("selected_doctor") or "Dr. K. Albert"

        def draw_watermark(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica-Bold', 32)
            canvas.setFillColor(colors.HexColor('#f8fafc')) # Very light clinical slate
            canvas.translate(297, 420)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, "STRATAFORM CLINICAL REPORT")
            canvas.restoreState()

        out_path = os.path.join(tempfile.gettempdir(), f"fitpulse_report_{uuid.uuid4().hex}.pdf")
        doc      = SimpleDocTemplate(out_path, pagesize=A4,
                                     leftMargin=1.5*cm, rightMargin=1.5*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
        styles   = getSampleStyleSheet()
        story    = []

        ORANGE = colors.HexColor("#0284c7") # Modern deep blue highlight instead of orange for Strataform
        DARK   = colors.HexColor("#0f172a") # Slate 900
        GRAY   = colors.HexColor("#475569") # Slate 600
        PEACH  = colors.HexColor("#f1f5f9") # Slate 100 for row backgrounds

        title_style = ParagraphStyle("Title", parent=styles["Title"],
                                     textColor=DARK, fontSize=20, fontName="Helvetica-Bold", spaceAfter=2, alignment=0)
        sub_style   = ParagraphStyle("Sub", parent=styles["Normal"],
                                     textColor=GRAY, fontSize=9, leading=12, spaceAfter=8)
        h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                     textColor=DARK, fontSize=12, fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6)
        body_style  = ParagraphStyle("Body", parent=styles["Normal"],
                                     textColor=DARK, fontSize=8.5, leading=11)
        body_bold   = ParagraphStyle("BodyBold", parent=styles["Normal"],
                                     textColor=DARK, fontSize=8.5, leading=11, fontName="Helvetica-Bold")
        body_muted  = ParagraphStyle("BodyMuted", parent=styles["Normal"],
                                     textColor=GRAY, fontSize=8, leading=11)

        # ── Clinic Hospital Letterhead ─────────────────────────────────────────
        story.append(Paragraph("STRATAFORM MEDICAL CENTER", title_style))
        story.append(Paragraph("12/32 Nethaji Street, Kodambakkam, 600 024 | diagnostics@strataform.med | 📞 044 2454 2454", sub_style))
        story.append(HRFlowable(width="100%", color=ORANGE, thickness=2, spaceAfter=10))

        # ── Metadata Grid ──────────────────────────────────────────────────────
        meta_data = [
            [Paragraph("<b>Report ID:</b>", body_style), Paragraph(str(uuid.uuid4())[:13].upper(), body_style),
             Paragraph("<b>Date Compiled:</b>", body_style), Paragraph(report['generated_at'], body_style)],
            [Paragraph("<b>Source File:</b>", body_style), Paragraph(filename, body_style),
             Paragraph("<b>Reviewed By:</b>", body_style), Paragraph(selected_doctor, body_bold)]
        ]
        meta_table = Table(meta_data, colWidths=[3.5*cm, 4.5*cm, 4*cm, 6*cm])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafaf9')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Clinical Summary Statistics Grid (Table) ──────────────────────────
        story.append(Paragraph("Clinical Summary Statistics", h2_style))
        stats = report.get("statistics", {})
        total_logs = str(stats.get("total_records", len(records or [])))
        
        val_hr = stats.get('avg_heart_rate')
        avg_hr = f"{round(val_hr)} bpm" if val_hr is not None else "72 bpm"
        val_spo2 = stats.get('avg_spo2')
        avg_spo2 = f"{round(val_spo2)}%" if val_spo2 is not None else "98%"
        val_sleep = stats.get('avg_sleep')
        avg_sleep = f"{val_sleep:.1f}h" if val_sleep is not None else "8.0h"
        val_stress = stats.get('avg_stress')
        avg_stress = f"{val_stress:.1f}/10" if val_stress is not None else "3.0/10"
        val_steps = stats.get('avg_steps')
        avg_steps = f"{val_steps:,.0f}" if val_steps is not None else "5,000"

        lbl_style = ParagraphStyle("StatLabel", parent=body_muted, fontSize=7, leading=9, alignment=1)
        val_style = ParagraphStyle("StatVal", parent=body_bold, fontSize=13, leading=15, alignment=1)

        def make_cell(label, value):
            return [
                Paragraph(label, lbl_style),
                Spacer(1, 2),
                Paragraph(value, val_style)
            ]

        stats_data = [
            [
                make_cell("TOTAL LOGS ADMISSIONS", total_logs),
                make_cell("RESTING MEAN HR", avg_hr),
                make_cell("AVERAGE SpO₂", avg_spo2)
            ],
            [
                make_cell("MEAN SLEEP DURATION", avg_sleep),
                make_cell("AVERAGE STRESS LEVEL", avg_stress),
                make_cell("AVERAGE DAILY STEPS", avg_steps)
            ]
        ]
        stats_table = Table(stats_data, colWidths=[6*cm, 6*cm, 6*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fafaf9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(stats_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Tabular Patient Records Table ──────────────────────────────────────
        story.append(Paragraph("Patient Health Log Records Table", h2_style))
        
        # Build tabular data
        # Columns: ID, Time, HR, BP, SpO2, Sleep, Steps, Stress, Risk
        table_headers = [
            Paragraph("<b>ID</b>", body_bold),
            Paragraph("<b>Timestamp</b>", body_bold),
            Paragraph("<b>Heart Rate</b>", body_bold),
            Paragraph("<b>BP (mmHg)</b>", body_bold),
            Paragraph("<b>SpO₂</b>", body_bold),
            Paragraph("<b>Sleep</b>", body_bold),
            Paragraph("<b>Steps</b>", body_bold),
            Paragraph("<b>Stress</b>", body_bold),
            Paragraph("<b>Risk Score</b>", body_bold)
        ]
        
        grid_data = [table_headers]
        
        target_records = records if records else []
        # Limit PDF records to latest 80 logs to prevent infinite pages, while giving a solid list
        if len(target_records) > 80:
            target_records = target_records[-80:]
            
        for idx, r in enumerate(target_records):
            r_id = r.get("id") or (idx + 1)
            time_str = r.get("timestamp", "—")
            hr = f"{r.get('heart_rate') or r.get('HeartRate') or 72:.0f} bpm"
            bp = f"{r.get('systolic_bp') or r.get('SystolicBP') or 120:.0f}/{r.get('diastolic_bp') or r.get('DiastolicBP') or 80:.0f}"
            spo2 = f"{r.get('spo2') or r.get('SpO2') or 98:.0f}%"
            sleep = f"{r.get('sleep_duration') or r.get('SleepDuration') or 8:.1f}h"
            steps = f"{r.get('steps') or r.get('Steps') or 0:,.0f}"
            stress = f"{r.get('stress_level') or r.get('StressLevel') or 3:.0f}/10"
            risk = f"{r.get('risk_score') or r.get('Risk_Score') or 0:.0f} ({r.get('risk_level') or r.get('Risk_Level') or 'Low'})"
            
            # Highlight anomaly risks
            if r.get("anomaly") == "Yes" or r.get("Anomaly") == "Yes":
                risk_p = Paragraph(f"<font color='red'><b>{risk} ⚠️</b></font>", body_bold)
            else:
                risk_p = Paragraph(risk, body_style)

            grid_data.append([
                Paragraph(f"#{r_id}", body_style),
                Paragraph(time_str, body_style),
                Paragraph(hr, body_style),
                Paragraph(bp, body_style),
                Paragraph(spo2, body_style),
                Paragraph(sleep, body_style),
                Paragraph(steps, body_style),
                Paragraph(stress, body_style),
                risk_p
            ])

        # Width of columns (Total width = 18cm)
        col_widths = [1.2*cm, 3.5*cm, 2*cm, 2*cm, 1.5*cm, 1.5*cm, 1.8*cm, 1.5*cm, 3*cm]
        logs_table = Table(grid_data, colWidths=col_widths, repeatRows=1)
        logs_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0), ORANGE),
            ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
            ("ALIGN",        (0,0), (-1,-1), "LEFT"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PEACH]),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING",      (0,0), (-1,-1), 4),
            ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ]))
        story.append(logs_table)
        story.append(Spacer(1, 0.5*cm))

        # ── Heart Rate Bar Chart ──────────────────────────────────────────────
        target_chart_records = target_records[-30:] if len(target_records) > 30 else target_records
        chart_data = []
        for r in target_chart_records:
            val = r.get('heart_rate') or r.get('HeartRate')
            if val is not None:
                chart_data.append(float(val))
            else:
                chart_data.append(72.0)

        if chart_data:
            story.append(Paragraph("Patient Heart Rate Diagnostics (Bar Chart)", h2_style))
            chart_drawing = Drawing(510, 140)
            chart = VerticalBarChart()
            chart.x = 25
            chart.y = 15
            chart.height = 110
            chart.width = 460
            chart.data = [chart_data]
            chart.categoryAxis.categoryNames = [str(idx + 1) for idx in range(len(chart_data))]
            chart.bars[0].fillColor = colors.HexColor("#0284c7") # Modern blue
            chart.valueAxis.valueMin = 40
            chart.valueAxis.valueMax = 150
            chart.valueAxis.valueStep = 20
            chart.categoryAxis.labels.fontSize = 6
            chart.valueAxis.labels.fontSize = 6
            chart_drawing.add(chart)
            story.append(chart_drawing)
            story.append(Spacer(1, 0.5*cm))

        # ── Insights summary ───────────────────────────────────────────────────
        if report.get("insights"):
            story.append(Paragraph("AI Diagnosis Briefing", h2_style))
            for ins in report["insights"][:3]: # Keep it to top 3 for spacing
                story.append(Paragraph(f"<b>• {ins['title']}</b>: {ins['detail']}", body_style))
                story.append(Spacer(1, 0.1*cm))
            story.append(Spacer(1, 0.4*cm))

        # Define centered styles to avoid XML tag parsing errors in ReportLab
        body_bold_center = ParagraphStyle("BodyBoldCenter", parent=body_bold, alignment=1)
        body_muted_center = ParagraphStyle("BodyMutedCenter", parent=body_muted, alignment=1, fontSize=7)

        # ── Centered Doctor Seal ──────────────────────────────────────────────
        seal_data = [
            [Paragraph("<b>STRATAFORM CLINICAL REVIEW</b>", body_bold_center)],
            [Paragraph(f"<b>🛡️ Authenticated Medical Evaluation — {selected_doctor} 🛡️</b>", body_bold_center)],
            [Paragraph("Certified Electronic Database Export Record<br/>Authorized Doctor Signatures Attached Below", body_muted_center)]
        ]
        seal_table = Table(seal_data, colWidths=[10*cm])
        seal_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.5, ORANGE),
            ('BACKGROUND', (0,0), (-1,-1), PEACH),
            ('PADDING', (0,0), (-1,-1), 6),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        layout_table = Table([[seal_table]], colWidths=[18*cm])
        layout_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(layout_table)
        story.append(Spacer(1, 0.5*cm))

        # ── Doctor Signatures (Dynamic based on selected doctor) ────────────────
        if "Suganya" in selected_doctor:
            sig_name = "Dr. D. Suganya, Ph.D."
            sig_title = "Lead Diagnostics Analyst"
        else:
            sig_name = "Dr. K. Albert, MD, FACC"
            sig_title = "Chief Cardiologist"

        sig_data = [
            ["", Paragraph(f"<b>{sig_name}</b>", body_style)],
            ["", Paragraph(f"<i>{sig_title}</i>", body_style)],
            ["", Paragraph("Strataform Medical Center (Project Purpose Only)", body_muted)]
        ]
        sig_table = Table(sig_data, colWidths=[12*cm, 6*cm])
        sig_table.setStyle(TableStyle([
            ('LINEABOVE', (1,0), (1,0), 0.75, colors.HexColor('#94a3b8')),
            ('PADDING', (0,0), (-1,-1), 1),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(sig_table)

        doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
        return out_path

    except Exception as e:
        import traceback
        traceback.print_exc()
        out_path = os.path.join(tempfile.gettempdir(), f"fitpulse_report_{uuid.uuid4().hex}.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("STRATAFORM HOSPITAL & CLINICAL LABS REPORT\n")
            f.write(f"Generated: {report.get('generated_at')}\n\n")
            f.write("TABULAR RECORD DATA\n")
            for r in (records or []):
                f.write(f"Log ID: {r.get('id')} | HR: {r.get('heart_rate')} | Risk: {r.get('risk_score')}\n")
        return out_path
