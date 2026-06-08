from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from PIL import ImageChops
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


FONT_NAME = "RepairNoticeChinese"


def _register_chinese_font() -> str:
    font_candidates = (
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simsunb.ttf"),
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    )

    for font_path in font_candidates:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
                return FONT_NAME
            except Exception:
                continue

    fallback = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(fallback))
    return fallback


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "NoticeTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "Heading": ParagraphStyle(
            "NoticeHeading",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=18,
            spaceBefore=8,
            spaceAfter=5,
            textColor=colors.HexColor("#1F4E79"),
            wordWrap="CJK",
        ),
        "Body": ParagraphStyle(
            "NoticeBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=15,
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "Small": ParagraphStyle(
            "NoticeSmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#555555"),
            wordWrap="CJK",
        ),
        "Cell": ParagraphStyle(
            "NoticeCell",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            wordWrap="CJK",
        ),
        "CellBold": ParagraphStyle(
            "NoticeCellBold",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8.5,
            leading=12,
            wordWrap="CJK",
            textColor=colors.HexColor("#222222"),
        ),
    }


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def _cell(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def _key_value_table(rows: list[tuple[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    normalized = []
    for index in range(0, len(rows), 2):
        left = rows[index]
        right = rows[index + 1] if index + 1 < len(rows) else ("", "")
        normalized.append(
            [
                _cell(left[0], styles["CellBold"]),
                _cell(left[1], styles["Cell"]),
                _cell(right[0], styles["CellBold"]),
                _cell(right[1], styles["Cell"]),
            ]
        )

    table = Table(normalized, colWidths=[27 * mm, 58 * mm, 27 * mm, 58 * mm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DF")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("BACKGROUND", (3, 0), (3, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _device_state_table(records: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [
        [
            _cell("部位", styles["CellBold"]),
            _cell("现状描述", styles["CellBold"]),
            _cell("客户确认", styles["CellBold"]),
        ]
    ]
    for record in records:
        data.append(
            [
                _cell(record.get("part", ""), styles["Cell"]),
                _cell(record.get("description") or "未填写", styles["Cell"]),
                _cell("已确认" if record.get("confirmed") else "未确认", styles["Cell"]),
            ]
        )

    table = Table(data, colWidths=[36 * mm, 105 * mm, 29 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DF")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _confirmation_table(risks: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[_cell("风险点", styles["CellBold"]), _cell("确认时间", styles["CellBold"])]]
    for risk in risks:
        data.append(
            [
                _cell(f"{risk.get('section', '')} - {risk.get('title', '')}", styles["Cell"]),
                _cell(risk.get("confirmed_at") or "未确认", styles["Cell"]),
            ]
        )

    table = Table(data, colWidths=[125 * mm, 45 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D3DF")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF1F8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _signature_flowable(signature_png: bytes, max_width: float = 75 * mm) -> Image:
    signature = PILImage.open(io.BytesIO(signature_png)).convert("RGBA")
    white = PILImage.new("RGBA", signature.size, "WHITE")
    composed = PILImage.alpha_composite(white, signature).convert("RGB")

    diff = ImageChops.difference(composed, PILImage.new("RGB", composed.size, "white"))
    bbox = diff.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        margin = 12
        cropped = composed.crop(
            (
                max(0, left - margin),
                max(0, top - margin),
                min(composed.width, right + margin),
                min(composed.height, bottom + margin),
            )
        )
    else:
        cropped = composed

    image_buffer = io.BytesIO()
    cropped.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    width, height = cropped.size
    draw_width = max_width
    draw_height = draw_width * height / width
    if draw_height > 35 * mm:
        draw_height = 35 * mm
        draw_width = draw_height * width / height

    flowable = Image(image_buffer, width=draw_width, height=draw_height)
    flowable.hAlign = "LEFT"
    return flowable


def _footer(font_name: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(18 * mm, 12 * mm, "电脑维修风险告知书")
        canvas.drawRightString(192 * mm, 12 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    return draw


def export_notice_pdf(payload: dict[str, Any]) -> bytes:
    """Build the notice PDF in memory only.

    Streamlit Cloud has a server-side filesystem. Returning bytes without
    writing a file keeps customer information out of cloud storage.
    """
    font_name = _register_chinese_font()
    styles = _styles(font_name)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=payload.get("title", "电脑维修风险告知书"),
    )

    story = [
        Paragraph(escape(payload.get("title", "电脑维修风险告知书")), styles["Title"]),
        _p(payload.get("intro", ""), styles["Body"]),
        Spacer(1, 5),
        Paragraph("一、客户与设备信息", styles["Heading"]),
        _key_value_table(payload.get("customer_info", []), styles),
        Spacer(1, 7),
        Paragraph("二、风险告知内容", styles["Heading"]),
    ]

    current_section = None
    for risk in payload.get("risks", []):
        if risk.get("section") != current_section:
            current_section = risk.get("section")
            story.append(_p(f"【{current_section}】", styles["Body"]))

        risk_block = [
            Paragraph(escape(f"{risk.get('title', '')}"), styles["Body"]),
            *[_p(f"• {paragraph}", styles["Body"]) for paragraph in risk.get("body", [])],
        ]
        story.append(KeepTogether(risk_block))

    story.extend(
        [
            Spacer(1, 6),
            Paragraph("三、客户确认声明", styles["Heading"]),
            *[_p(f"• {line}", styles["Body"]) for line in payload.get("customer_declarations", [])],
            Spacer(1, 6),
            Paragraph("四、逐项风险确认记录", styles["Heading"]),
            _confirmation_table(payload.get("risks", []), styles),
            Spacer(1, 7),
            Paragraph("五、设备接机状态记录", styles["Heading"]),
            _device_state_table(payload.get("device_records", []), styles),
            Spacer(1, 8),
            Paragraph("六、电子签名与最终确认", styles["Heading"]),
        ]
    )

    signature_png = payload.get("signature_png")
    signature_rows = [
        ("签名确认时间", payload.get("signature_confirmed_at", "")),
        ("最终确认按钮", payload.get("final_confirm_text", "")),
        ("最终确认时间", payload.get("final_confirmed_at", "")),
        ("PDF 生成时间", payload.get("generated_at", "")),
    ]
    story.append(_key_value_table(signature_rows, styles))
    story.append(Spacer(1, 7))
    if signature_png:
        story.append(_p("客户签名：", styles["Body"]))
        story.append(_signature_flowable(signature_png))
    story.append(Spacer(1, 8))
    story.append(
        _p(
            "本文件由系统记录客户逐项确认、电子签名及最终点击“已确认以上风险”后生成。",
            styles["Small"],
        )
    )

    doc.build(story, onFirstPage=_footer(font_name), onLaterPages=_footer(font_name))
    return buffer.getvalue()
