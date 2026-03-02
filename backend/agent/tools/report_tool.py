from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_pdf_report(
    content: dict,
    company_name: str,
    run_id: str,
    reports_dir: str = "reports",
) -> str:
    """Generate a PDF financial analysis report using reportlab.

    Args:
        content: dict with keys like "summary", "market_data", "ratios",
                 "alerts_summary", "key_findings", "news_headlines"
        company_name: Display name for the company
        run_id: Agent run UUID string (used in filename)
        reports_dir: Directory to save the PDF

    Returns:
        Absolute path to the generated PDF file.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        Path(reports_dir).mkdir(parents=True, exist_ok=True)
        filename = f"report_{run_id}.pdf"
        filepath = str(Path(reports_dir) / filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18,
                                     textColor=colors.HexColor("#1a3c6e"), spaceAfter=12)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13,
                                  textColor=colors.HexColor("#2c5f9e"), spaceAfter=6)
        body_style = styles["BodyText"]
        body_style.fontSize = 10

        story = []

        # Title
        story.append(Paragraph(f"Financial Analysis Report: {company_name}", title_style))
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", body_style))
        story.append(Paragraph(f"Run ID: {run_id}", body_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2c5f9e")))
        story.append(Spacer(1, 12))

        # Executive Summary
        if content.get("summary"):
            story.append(Paragraph("Executive Summary", h2_style))
            story.append(Paragraph(str(content["summary"]), body_style))
            story.append(Spacer(1, 10))

        # Key Findings
        if content.get("key_findings"):
            story.append(Paragraph("Key Findings", h2_style))
            for finding in content["key_findings"]:
                story.append(Paragraph(f"• {finding}", body_style))
            story.append(Spacer(1, 10))

        # Market Data Table
        if content.get("market_data"):
            story.append(Paragraph("Market Data", h2_style))
            md = content["market_data"]
            table_data = [["Metric", "Value"]]
            for k, v in md.items():
                if k != "error":
                    table_data.append([str(k).replace("_", " ").title(), str(v)])
            if len(table_data) > 1:
                t = Table(table_data, colWidths=[8*cm, 8*cm])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f9e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))

        # Financial Ratios Table
        if content.get("ratios"):
            story.append(Paragraph("Financial Ratios", h2_style))
            ratios = content["ratios"]
            table_data = [["Ratio", "Value", "Interpretation"]]
            for k, v in ratios.items():
                table_data.append([
                    str(k).replace("_", " ").title(),
                    str(v.get("value", "N/A")),
                    str(v.get("interpretation", "")),
                ])
            t = Table(table_data, colWidths=[7*cm, 4*cm, 5*cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5f9e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))

        # Alerts Summary
        if content.get("alerts_summary"):
            story.append(Paragraph("Alerts Summary", h2_style))
            for alert in content["alerts_summary"]:
                story.append(Paragraph(f"[{alert.get('level','').upper()}] {alert.get('message','')}", body_style))
            story.append(Spacer(1, 10))

        # News Headlines
        if content.get("news_headlines"):
            story.append(Paragraph("Recent News", h2_style))
            for item in content["news_headlines"]:
                story.append(Paragraph(f"• {item}", body_style))
            story.append(Spacer(1, 10))

        doc.build(story)
        logger.info("Generated PDF report: %s", filepath)
        return filepath

    except Exception as e:
        logger.exception("PDF generation failed: %s", e)
        return ""
