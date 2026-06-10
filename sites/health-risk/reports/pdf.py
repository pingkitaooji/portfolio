from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_NAME = "STSong-Light"
PAGE_WIDTH, PAGE_HEIGHT = A4


def create_sample_pdf(report_serial, patient, snp_record, risks, medical_advice=None, disclaimer=""):
    # Build a polished demo PDF report entirely in memory before saving it.
    register_fonts()
    buffer = BytesIO()
    styles = build_styles()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"{report_serial} 健康風險評估報告系統",
        author="健康風險評估報告系統",
    )

    story = [
        build_header(report_serial, styles),
        Spacer(1, 8 * mm),
        build_meta_table(patient, snp_record, styles),
        Spacer(1, 7 * mm),
        section_title("風險摘要", styles),
        build_risk_table(risks, styles),
        Spacer(1, 7 * mm),
        section_title("固定醫療建議", styles),
        *build_advice_blocks(medical_advice or [], styles),
        Spacer(1, 5 * mm),
        build_disclaimer(disclaimer, styles),
    ]

    doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)
    return buffer.getvalue()


def register_fonts():
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def build_styles():
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "Brand",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#0f766e"),
            alignment=TA_LEFT,
            wordWrap="CJK",
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=20,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
            wordWrap="CJK",
        ),
        "logo": ParagraphStyle(
            "Logo",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=12,
            leading=14,
            textColor=colors.white,
            alignment=TA_CENTER,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            wordWrap="CJK",
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            wordWrap="CJK",
        ),
        "value": ParagraphStyle(
            "Value",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            wordWrap="CJK",
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#115e59"),
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=15,
            textColor=colors.HexColor("#334155"),
            wordWrap="CJK",
        ),
        "center": ParagraphStyle(
            "Center",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_CENTER,
            wordWrap="CJK",
        ),
        "right": ParagraphStyle(
            "Right",
            parent=base["Normal"],
            fontName=FONT_NAME,
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#475569"),
            alignment=TA_RIGHT,
            wordWrap="CJK",
        ),
    }


def build_header(report_serial, styles):
    logo = Table(
        [[Paragraph("HR", styles["logo"])]],
        colWidths=[18 * mm],
        rowHeights=[18 * mm],
    )
    logo.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#0f766e")),
            ]
        )
    )
    left = [
        Paragraph("健康風險評估報告系統", styles["brand"]),
        Paragraph("健康風險評估報告系統", styles["title"]),
        Paragraph("Health Risk Assessment Report System", styles["small"]),
    ]
    right = [
        Paragraph(f"報告編號<br/>{report_serial}", styles["right"]),
        Paragraph(f"產生時間<br/>{datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["right"]),
    ]
    table = Table(
        [[logo, left, right]],
        colWidths=[22 * mm, 98 * mm, 39 * mm],
        rowHeights=[29 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def build_meta_table(patient, snp_record, styles):
    rows = [
        [
            meta_cell("病人名稱", patient.name, styles),
            meta_cell("性別", patient.get_gender_display(), styles),
            meta_cell("醫院端流水號", patient.hospital_serial, styles),
        ],
        [
            meta_cell("樣本流水號", snp_record.server_serial, styles),
            meta_cell("SNP 筆數", str(snp_record.snp_count), styles),
            meta_cell("報告屬性", "DEMO / 非臨床診斷", styles),
        ],
        [
            meta_cell("PC Check", "通過" if snp_record.pc_check_passed else "未通過", styles),
            meta_cell("NC Check", "通過" if snp_record.nc_check_passed else "未通過", styles),
            meta_cell("資料來源", "SNP 上傳檔案", styles),
        ],
    ]
    table = Table(rows, colWidths=[53 * mm, 53 * mm, 53 * mm], rowHeights=[20 * mm] * 3)
    table.setStyle(card_table_style())
    return table


def meta_cell(label, value, styles):
    return [
        Paragraph(label, styles["label"]),
        Spacer(1, 1.5 * mm),
        Paragraph(value, styles["value"]),
    ]


def section_title(text, styles):
    return KeepTogether(
        [
            Paragraph(text, styles["section"]),
            Spacer(1, 2.5 * mm),
        ]
    )


def build_risk_table(risks, styles):
    # ReportLab tables keep the generated PDF structured and easy to scan.
    rows = [[
        Paragraph("風險項目", styles["center"]),
        Paragraph("等級", styles["center"]),
        Paragraph("分數", styles["center"]),
        Paragraph("摘要", styles["center"]),
    ]]
    for risk in risks:
        rows.append(
            [
                Paragraph(risk.get("name", "-"), styles["body"]),
                Paragraph(risk.get("level", "-"), styles["center"]),
                Paragraph(str(risk.get("score", "-")), styles["center"]),
                Paragraph(risk.get("note", "-"), styles["body"]),
            ]
        )
    table = Table(rows, colWidths=[42 * mm, 22 * mm, 18 * mm, 77 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def build_advice_blocks(medical_advice, styles):
    blocks = []
    for item in medical_advice:
        table = Table(
            [
                [
                    Paragraph(
                        f"{item.get('risk_name', '風險項目')} / {item.get('level', '-')}",
                        styles["value"],
                    )
                ],
                [Paragraph(item.get("recommendation", ""), styles["body"])],
            ],
            colWidths=[159 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#99f6e4")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        blocks.append(KeepTogether([table, Spacer(1, 3 * mm)]))
    if not blocks:
        blocks.append(Paragraph("尚未建立醫療建議。", styles["body"]))
    return blocks


def build_disclaimer(disclaimer, styles):
    table = Table(
        [
            [Paragraph("免責聲明", styles["value"])],
            [Paragraph(disclaimer or "本報告僅供展示，不作為臨床診斷依據。", styles["body"])],
        ],
        colWidths=[159 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7ed")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fdba74")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def card_table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]
    )


def draw_page_frame(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(colors.HexColor("#0f766e"))
    canvas.rect(0, PAGE_HEIGHT - 8 * mm, PAGE_WIDTH, 8 * mm, fill=True, stroke=False)
    canvas.setStrokeColor(colors.HexColor("#dbeafe"))
    canvas.setLineWidth(0.6)
    canvas.line(18 * mm, 14 * mm, PAGE_WIDTH - 18 * mm, 14 * mm)
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(18 * mm, 9 * mm, "健康風險評估報告系統")
    canvas.drawRightString(PAGE_WIDTH - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()
