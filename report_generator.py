"""
report_generator.py
Implements ReportGenerator from the Class Diagram: generateReport(), exportPDF().
Covers FR-06.4 (Export incident summary report) from the SRS.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports")


class ReportGenerator:
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, file_name: str, stats: dict, incidents: list):
        """Builds the in-memory report content structure (title + sections)."""
        return {
            "title": f"LogMiner Incident Summary — {file_name}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stats": stats,
            "incidents": incidents,
        }

    def export_pdf(self, report: dict) -> str:
        safe_name = "".join(c if c.isalnum() else "_" for c in report["title"])[:60]
        out_path = os.path.join(self.output_dir, f"{safe_name}.pdf")

        doc = SimpleDocTemplate(out_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(report["title"], styles["Title"]),
            Paragraph(f"Generated: {report['generated_at']}", styles["Normal"]),
            Spacer(1, 16),
            Paragraph("Summary Statistics", styles["Heading2"]),
        ]

        stats_table = Table(
            [["Metric", "Value"]] + [[k, str(v)] for k, v in report["stats"].items()],
            colWidths=[220, 220],
        )
        stats_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E4A7D")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(stats_table)
        story.append(Spacer(1, 20))
        story.append(Paragraph("Detected Incidents & Root Causes", styles["Heading2"]))

        if not report["incidents"]:
            story.append(Paragraph("No anomalies were detected above the configured threshold.", styles["Normal"]))
        else:
            for i, inc in enumerate(report["incidents"], start=1):
                story.append(Paragraph(f"Incident {i} — Severity: {inc['severity']}", styles["Heading3"]))
                story.append(Paragraph(inc["root_cause_msg"], styles["Normal"]))
                if inc["evidence"]:
                    story.append(Paragraph("Evidence: " + "; ".join(inc["evidence"]), styles["Normal"]))
                story.append(Spacer(1, 10))

        doc.build(story)
        return out_path
