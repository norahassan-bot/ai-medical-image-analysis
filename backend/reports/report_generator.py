"""Clinical PDF Report Generation Service for AI Medical Image Analysis.

Generates standardized clinical decision-support PDF reports from real
persisted SQLite analysis records and Grad-CAM visualizations.

Design & Compliance:
--------------------
1. Report Title: AI Medical Image Analysis Report
2. Sections: Analysis Information, Diagnostic Prediction, Visual Explainability, Regulatory Disclaimer
3. Caching: Re-uses previously generated PDFs for identical analysis records.
4. Security: Safe path resolution with strict directory traversal prevention.
5. Image Handling: Proportional aspect-ratio scaling for medical radiographs.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from datetime import datetime

from PIL import Image as PILImage
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    HRFlowable,
)

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from database.database import (
    get_analysis_by_id,
    get_default_db_path,
    get_default_storage_dir,
)

logger = logging.getLogger("ReportGenerator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WORKSPACE_ROOT = backend_root.parent
DEFAULT_REPORTS_DIR = WORKSPACE_ROOT / "reports" / "pdf"


def get_default_report_dir() -> Path:
    """Resolve default destination directory for generated PDF reports."""
    env_dir = os.getenv("PDF_REPORTS_DIR")
    if env_dir:
        return Path(env_dir)
    return DEFAULT_REPORTS_DIR


def get_report_path(
    analysis_id: str,
    output_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """Generate canonical sanitized PDF file path for an analysis ID."""
    if not analysis_id or not isinstance(analysis_id, str):
        raise ValueError("Invalid analysis ID.")
    if ".." in analysis_id or "/" in analysis_id or "\\" in analysis_id:
        raise ValueError(f"Path traversal detected in analysis ID: {analysis_id}")
    if not all(c.isalnum() or c in "-_" for c in analysis_id):
        raise ValueError(f"Invalid characters in analysis ID: {analysis_id}")
    target_dir = Path(output_dir) if output_dir else get_default_report_dir()
    return target_dir / f"analysis_{analysis_id}.pdf"


def resolve_safe_image_path(
    reference: Optional[str],
    storage_base: Optional[Path] = None,
) -> Optional[Path]:
    """Safely resolve an image reference within the configured storage directory.

    Guarantees that path traversal (e.g. '../') cannot access unauthorized files.
    """
    if not reference:
        return None

    base_dir = (storage_base or get_default_storage_dir()).resolve()
    target_path = (base_dir / reference).resolve()

    # Prevent directory traversal attacks
    if not str(target_path).startswith(str(base_dir)):
        logger.warning(f"Rejected unsafe image path traversal attempt: {reference}")
        return None

    if target_path.exists() and target_path.is_file():
        return target_path

    # Fallback to check relative to backend data directory
    alt_base = (backend_root / "data" / "visualizations").resolve()
    alt_target = (alt_base / reference).resolve()
    if str(alt_target).startswith(str(alt_base)) and alt_target.exists() and alt_target.is_file():
        return alt_target

    return None


def create_scaled_image(
    img_path: Path,
    max_width: float = 160.0,
    max_height: float = 160.0,
) -> Optional[RLImage]:
    """Create a ReportLab Image flowable with proportional aspect-ratio scaling."""
    try:
        with PILImage.open(img_path) as pil_img:
            orig_w, orig_h = pil_img.size

        if orig_w <= 0 or orig_h <= 0:
            return None

        # Calculate aspect ratio
        ratio = min(max_width / orig_w, max_height / orig_h)
        scaled_w = orig_w * ratio
        scaled_h = orig_h * ratio

        return RLImage(str(img_path), width=scaled_w, height=scaled_h)
    except Exception as e:
        logger.warning(f"Failed opening image for PDF inclusion: {img_path} ({e})")
        return None


def generate_analysis_pdf(
    analysis_id: str,
    db_path: Optional[Union[str, Path]] = None,
    output_dir: Optional[Union[str, Path]] = None,
    force_regenerate: bool = False,
) -> Path:
    """Generate a clinical decision-support PDF report for a stored analysis.

    Args:
        analysis_id: Unique UUID string of stored analysis.
        db_path: Path to SQLite database.
        output_dir: Target destination directory for PDF reports.
        force_regenerate: If True, regenerates PDF even if it already exists.

    Returns:
        Path to the generated/cached PDF file.
    """
    pdf_path = get_report_path(analysis_id, output_dir=output_dir)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Check Cache
    if pdf_path.exists() and pdf_path.stat().st_size > 0 and not force_regenerate:
        logger.info(f"Reusing cached PDF report at: {pdf_path}")
        return pdf_path

    # 2. Retrieve actual analysis record from SQLite
    record = get_analysis_by_id(analysis_id, db_path=db_path)
    if not record:
        raise FileNotFoundError(f"Analysis record with ID '{analysis_id}' not found in database.")

    logger.info(f"Generating new PDF report for analysis {analysis_id} -> {pdf_path}")

    # 3. Initialize Document Template
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="AI Medical Image Analysis Report",
        author="AI Medical Imaging Platform",
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0d9488"),
        spaceAfter=12,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    bold_label = ParagraphStyle(
        "BoldLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#78350f"),
    )

    story: List[Any] = []

    # -------------------------------------------------------------------------
    # Header & Title
    # -------------------------------------------------------------------------
    story.append(Paragraph("AI Medical Image Analysis Report", title_style))
    story.append(
        Paragraph(
            "Chest Radiograph Clinical Decision Support System &bull; NORMAL vs PNEUMONIA",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0d9488"), spaceAfter=12))

    # -------------------------------------------------------------------------
    # Section 1: Analysis Information
    # -------------------------------------------------------------------------
    story.append(Paragraph("Analysis Information", section_heading))

    raw_date = record.get("created_at", "")
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        formatted_date = raw_date

    info_data = [
        [
            Paragraph("Analysis ID:", bold_label),
            Paragraph(str(record.get("analysis_id", "N/A")), body_style),
            Paragraph("Date & Time:", bold_label),
            Paragraph(formatted_date, body_style),
        ],
        [
            Paragraph("Model Version:", bold_label),
            Paragraph(f"v{record.get('model_version', '1.0.0')}", body_style),
            Paragraph("Architecture:", bold_label),
            Paragraph(str(record.get("architecture", "resnet18")).upper(), body_style),
        ],
        [
            Paragraph("Execution Device:", bold_label),
            Paragraph(str(record.get("device", "cpu")).upper(), body_style),
            Paragraph("Inference Latency:", bold_label),
            Paragraph(f"{record.get('inference_time_ms', 0):.2f} ms", body_style),
        ],
    ]

    info_table = Table(info_data, colWidths=[90, 180, 90, 180])
    info_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # Section 2: Diagnostic Prediction & Probabilities
    # -------------------------------------------------------------------------
    story.append(Paragraph("Diagnostic Prediction", section_heading))

    prediction = str(record.get("prediction", "UNKNOWN")).upper()
    confidence = float(record.get("confidence", 0.0))
    conf_pct = f"{confidence * 100:.2f}%"

    is_pneumonia = prediction == "PNEUMONIA"
    pred_bg = colors.HexColor("#fef3c7") if is_pneumonia else colors.HexColor("#ecfdf5")
    pred_border = colors.HexColor("#f59e0b") if is_pneumonia else colors.HexColor("#10b981")
    pred_color = colors.HexColor("#b45309") if is_pneumonia else colors.HexColor("#047857")

    pred_title_style = ParagraphStyle(
        "PredResult",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=pred_color,
    )

    probabilities = record.get("probabilities", {})
    norm_prob = probabilities.get("NORMAL", 1 - confidence if is_pneumonia else confidence)
    pneu_prob = probabilities.get("PNEUMONIA", confidence if is_pneumonia else 1 - confidence)

    pred_data = [
        [
            Paragraph(f"Predicted Class: <b>{prediction}</b>", pred_title_style),
            Paragraph(f"Confidence: <b>{conf_pct}</b>", pred_title_style),
        ],
        [
            Paragraph(f"NORMAL Probability: <b>{norm_prob * 100:.2f}%</b>", body_style),
            Paragraph(f"PNEUMONIA Probability: <b>{pneu_prob * 100:.2f}%</b>", body_style),
        ],
    ]

    pred_table = Table(pred_data, colWidths=[270, 270])
    pred_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), pred_bg),
            ("BOX", (0, 0), (-1, -1), 1, pred_border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(pred_table)
    story.append(Spacer(1, 10))

    # -------------------------------------------------------------------------
    # Section 3: Visual Explainability (Original, Heatmap, Overlay)
    # -------------------------------------------------------------------------
    story.append(Paragraph("Visual Explainability (Grad-CAM)", section_heading))

    orig_img_path = resolve_safe_image_path(record.get("image_reference"))
    heat_img_path = resolve_safe_image_path(record.get("heatmap_reference"))
    over_img_path = resolve_safe_image_path(record.get("overlay_reference"))

    rl_orig = create_scaled_image(orig_img_path, 165, 165) if orig_img_path else Paragraph("Image not available", body_style)
    rl_heat = create_scaled_image(heat_img_path, 165, 165) if heat_img_path else Paragraph("Heatmap not available", body_style)
    rl_over = create_scaled_image(over_img_path, 165, 165) if over_img_path else Paragraph("Overlay not available", body_style)

    img_table_data = [
        [
            Paragraph("<b>Original X-Ray</b>", ParagraphStyle("HdrC", parent=body_style, alignment=1)),
            Paragraph("<b>AI Activation Heatmap</b>", ParagraphStyle("HdrC", parent=body_style, alignment=1)),
            Paragraph("<b>Grad-CAM Overlay</b>", ParagraphStyle("HdrC", parent=body_style, alignment=1)),
        ],
        [rl_orig, rl_heat, rl_over],
    ]

    vis_table = Table(img_table_data, colWidths=[180, 180, 180])
    vis_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(vis_table)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------------------------
    # Section 4: Regulatory & Clinical Disclaimer
    # -------------------------------------------------------------------------
    disclaimer_text = (
        "<b>CLINICAL & REGULATORY DISCLAIMER:</b> This report is generated by an AI system "
        "for research and educational/decision-support purposes. It is not a medical diagnosis "
        "and must be reviewed by a qualified healthcare professional."
    )

    disc_data = [[Paragraph(disclaimer_text, disclaimer_style)]]
    disc_table = Table(disc_data, colWidths=[540])
    disc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f59e0b")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(disc_table)

    # 4. Build PDF Document
    doc.build(story)
    logger.info(f"Successfully compiled PDF report: {pdf_path}")
    return pdf_path
