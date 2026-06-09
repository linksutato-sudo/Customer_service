from __future__ import annotations

import io
import re
from datetime import datetime

import numpy as np
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

from notice_content import (
    CUSTOMER_DECLARATIONS,
    DEVICE_STATE_PARTS,
    NOTICE_INTRO,
    NOTICE_TITLE,
    RISK_ITEMS,
)
from pdf_exporter import export_notice_pdf


DEVICE_STATE_OPTIONS: tuple[str, ...] = (
    "无异常",
    "划痕",
    "凹陷",
    "掉漆",
    "裂纹",
    "缺螺丝",
    "松动",
    "变形",
    "无法检查",
    "未随机器",
)


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    return cleaned or "客户"


def init_state() -> None:
    risk_ids = {risk.id for risk in RISK_ITEMS}
    saved = st.session_state.get("risk_confirmed_at")
    if not isinstance(saved, dict) or set(saved.keys()) != risk_ids:
        st.session_state.risk_confirmed_at = {risk.id: "" for risk in RISK_ITEMS}

    defaults = {
        "signature_png": None,
        "signature_confirmed": False,
        "signature_confirmed_at": "",
        "final_confirmed_at": "",
        "pdf_bytes": None,
        "pdf_file_name": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def reset_all() -> None:
    for key in list(st.session_state.keys()):
        if (
            key.startswith("risk_")
            or key.startswith("signature_")
            or key.startswith("pdf_")
            or key.startswith("state_desc_")
            or key.startswith("state_options_")
            or key.startswith("state_remark_")
            or key.startswith("state_confirmed_")
            or key
            in {
                "customer_name",
                "customer_phone",
                "device_model",
                "serial_number",
                "reported_issue",
                "receiver_name",
                "warranty_days",
                "data_backup_status",
                "old_part_policy",
                "password_authorization",
                "repair_notes",
                "final_confirmed_at",
            }
        ):
            del st.session_state[key]
    init_state()


def canvas_has_ink(image_data: np.ndarray | None) -> bool:
    if image_data is None:
        return False
    image = np.asarray(image_data)
    if image.ndim < 3 or image.shape[-1] < 3:
        return False
    rgb = image[..., :3].astype(np.uint8)
    return bool(np.any(np.min(rgb, axis=2) < 245))


def canvas_to_png_bytes(image_data: np.ndarray) -> bytes:
    image = Image.fromarray(image_data.astype(np.uint8)).convert("RGBA")
    white = Image.new("RGBA", image.size, "WHITE")
    white.alpha_composite(image)
    output = io.BytesIO()
    white.convert("RGB").save(output, format="PNG")
    return output.getvalue()


def risk_payload() -> list[dict[str, object]]:
    return [
        {
            "id": risk.id,
            "section": risk.section,
            "title": risk.title,
            "body": list(risk.body),
            "confirmed_at": st.session_state.risk_confirmed_at.get(risk.id, ""),
        }
        for risk in RISK_ITEMS
    ]


def customer_info_rows() -> list[tuple[str, object]]:
    return [
        ("客户姓名", st.session_state.get("customer_name", "")),
        ("联系电话", st.session_state.get("customer_phone", "")),
        ("设备型号", st.session_state.get("device_model", "")),
        ("序列号/资产编号", st.session_state.get("serial_number", "")),
        ("报修故障现象", st.session_state.get("reported_issue", "")),
        ("接机员/经办人", st.session_state.get("receiver_name", "")),
        ("重要数据备份", st.session_state.get("data_backup_status", "")),
        ("旧件处理", st.session_state.get("old_part_policy", "")),
        ("保修天数", f"{st.session_state.get('warranty_days', 30)} 天"),
        ("账号/密码授权", st.session_state.get("password_authorization", "")),
        ("其他备注", st.session_state.get("repair_notes", "")),
    ]


def device_records() -> list[dict[str, object]]:
    records = []
    for index, part in enumerate(DEVICE_STATE_PARTS):
        selected_states = st.session_state.get(f"state_options_{index}", [])
        remark = st.session_state.get(f"state_remark_{index}", "").strip()
        description_parts = []
        if selected_states:
            description_parts.append("、".join(selected_states))
        if remark:
            description_parts.append(f"备注：{remark}")

        records.append(
            {
                "part": part,
                "description": "；".join(description_parts),
                "confirmed": st.session_state.get(f"state_confirmed_{index}", False),
            }
        )
    return records


def build_payload(final_confirmed_at: str) -> dict[str, object]:
    return {
        "title": NOTICE_TITLE,
        "intro": NOTICE_INTRO,
        "customer_info": customer_info_rows(),
        "risks": risk_payload(),
        "customer_declarations": list(CUSTOMER_DECLARATIONS),
        "device_records": device_records(),
        "signature_png": st.session_state.signature_png,
        "signature_confirmed_at": st.session_state.signature_confirmed_at,
        "final_confirm_text": "已确认以上风险",
        "final_confirmed_at": final_confirmed_at,
        "generated_at": now_text(),
    }


def required_missing() -> list[str]:
    required = {
        "客户姓名": st.session_state.get("customer_name", "").strip(),
        "联系电话": st.session_state.get("customer_phone", "").strip(),
        "设备型号": st.session_state.get("device_model", "").strip(),
    }
    return [label for label, value in required.items() if not value]


st.set_page_config(page_title=NOTICE_TITLE, page_icon="🛠️", layout="wide")
init_state()

st.markdown(
    """
    <style>
    .stButton > button { width: 100%; }
    .small-muted { color: #667085; font-size: 0.9rem; }
    .risk-ok { color: #027A48; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title(NOTICE_TITLE)
st.write(NOTICE_INTRO)

with st.sidebar:
    st.subheader("流程状态")
    confirmed_count = sum(1 for value in st.session_state.risk_confirmed_at.values() if value)
    st.metric("风险确认", f"{confirmed_count}/{len(RISK_ITEMS)}")
    st.progress(confirmed_count / len(RISK_ITEMS), text="全部确认后开放客户签名")
    if st.session_state.signature_confirmed:
        st.success("客户签名已确认")
    if st.session_state.pdf_file_name:
        st.success("PDF 已生成，待下载")
    if st.button("重新开始", help="清空本次页面填写、确认、签名和 PDF 状态。"):
        reset_all()
        st.rerun()

st.header("客户与设备信息")
info_left, info_mid, info_right = st.columns(3)
with info_left:
    st.text_input("客户姓名 *", key="customer_name", placeholder="请输入客户姓名")
    st.text_input("联系电话 *", key="customer_phone", placeholder="请输入联系电话")
    st.text_input("接机员/经办人", key="receiver_name", placeholder="请输入经办人姓名")
with info_mid:
    st.text_input("设备品牌/型号 *", key="device_model", placeholder="如：Lenovo ThinkPad X1")
    st.text_input("序列号/资产编号", key="serial_number", placeholder="SN、资产编号或其他标识")
    st.number_input("修复故障点保修天数", min_value=0, max_value=365, value=30, step=1, key="warranty_days")
with info_right:
    st.selectbox(
        "重要数据备份确认",
        options=("已自行备份并接受数据风险", "设备无法备份/不需要备份，知悉并接受风险", "尚未备份"),
        key="data_backup_status",
    )
    st.selectbox(
        "旧件处理",
        options=("无需保留旧件", "需要保留旧件并在取机时当场取走", "待维修方案确认后再决定"),
        key="old_part_policy",
    )
    st.text_input("账号/密码授权说明", key="password_authorization", placeholder="现场输入/临时密码/不提供密码等")

st.text_area("报修故障现象", key="reported_issue", placeholder="请简要描述客户反馈的故障现象。")
st.text_area("其他备注", key="repair_notes", placeholder="可填写配件来源、报价说明、客户特殊要求等。")

with st.expander("设备接机状态记录", expanded=False):
    st.caption("建议接机时与客户共同核对外观和附件状态，取机或争议处理时更清楚。")
    for index, part in enumerate(DEVICE_STATE_PARTS):
        state_col, remark_col, ok_col = st.columns([4, 3, 1])
        with state_col:
            st.pills(
                f"{part} 状态",
                options=DEVICE_STATE_OPTIONS,
                selection_mode="multi",
                key=f"state_options_{index}",
            )
        with remark_col:
            st.text_input(
                f"{part} 备注",
                key=f"state_remark_{index}",
                placeholder="补充位置、数量、程度等",
            )
        with ok_col:
            st.checkbox("客户确认", key=f"state_confirmed_{index}")

st.header("风险告知逐项确认")
for risk in RISK_ITEMS:
    confirmed_at = st.session_state.risk_confirmed_at.get(risk.id, "")
    title = f"{risk.section}｜{risk.title}"
    with st.expander(title, expanded=not bool(confirmed_at)):
        for paragraph in risk.body:
            st.markdown(f"- {paragraph}")

        action_col, status_col = st.columns([1, 2])
        with action_col:
            if confirmed_at:
                if st.button("已确认", key=f"confirmed_{risk.id}", disabled=True):
                    pass
            else:
                if st.button(f"确认此风险点", key=f"confirm_{risk.id}"):
                    st.session_state.risk_confirmed_at[risk.id] = now_text()
                    st.session_state.signature_confirmed = False
                    st.session_state.signature_png = None
                    st.session_state.pdf_bytes = None
                    st.session_state.pdf_file_name = ""
                    st.rerun()
        with status_col:
            if confirmed_at:
                st.markdown(f'<span class="risk-ok">已确认：{confirmed_at}</span>', unsafe_allow_html=True)
            else:
                st.info("请客户阅读后点击左侧确认按钮。")

all_risks_confirmed = all(st.session_state.risk_confirmed_at.values())

st.header("客户签名")
if not all_risks_confirmed:
    st.warning("请先逐项确认全部风险点，签名区域将在全部确认后开启。")
else:
    if not st.session_state.signature_confirmed:
        st.caption("请客户在下方白色区域手写签名。签名确认后如重新确认风险或重签，将重新生成 PDF。")
        canvas_result = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=3,
            stroke_color="#111111",
            background_color="#FFFFFF",
            height=220,
            width=760,
            drawing_mode="freedraw",
            display_toolbar=True,
            update_streamlit=True,
            key="signature_canvas",
        )
        has_signature = canvas_has_ink(canvas_result.image_data)
        if st.button("确认签名", type="primary", disabled=not has_signature):
            st.session_state.signature_png = canvas_to_png_bytes(canvas_result.image_data)
            st.session_state.signature_confirmed = True
            st.session_state.signature_confirmed_at = now_text()
            st.session_state.pdf_bytes = None
            st.session_state.pdf_file_name = ""
            st.rerun()
        if not has_signature:
            st.info("签名区域尚未检测到笔迹。")
    else:
        st.success(f"签名已确认：{st.session_state.signature_confirmed_at}")
        st.image(st.session_state.signature_png, caption="客户签名", width=380)
        if st.button("重新签名"):
            st.session_state.signature_confirmed = False
            st.session_state.signature_png = None
            st.session_state.signature_confirmed_at = ""
            st.session_state.pdf_bytes = None
            st.session_state.pdf_file_name = ""
            st.rerun()

st.header("最终确认与 PDF 下载")
if not st.session_state.signature_confirmed:
    st.info("客户确认签名后，将显示“已确认以上风险”按钮并生成可下载 PDF。")
else:
    missing = required_missing()
    if missing:
        st.warning("生成 PDF 前请补充：" + "、".join(missing))

    if st.button("已确认以上风险", type="primary", disabled=bool(missing)):
        final_time = now_text()
        customer_name = safe_filename(st.session_state.get("customer_name", "客户"))
        device_name = safe_filename(st.session_state.get("device_model", "设备"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"电脑维修风险告知书_{customer_name}_{device_name}_{timestamp}.pdf"
        payload = build_payload(final_time)
        st.session_state.pdf_bytes = export_notice_pdf(payload)
        st.session_state.pdf_file_name = file_name
        st.session_state.final_confirmed_at = final_time
        st.success("PDF 已在本次会话中生成，请点击下方按钮下载到本地。")

if st.session_state.pdf_bytes:
    st.download_button(
        label="下载 PDF",
        data=st.session_state.pdf_bytes,
        file_name=st.session_state.pdf_file_name,
        mime="application/pdf",
    )
    st.caption("隐私模式：PDF 仅保存在当前会话内存中，不写入云端文件系统。下载完成后可点击侧边栏“重新开始”清空页面状态。")
