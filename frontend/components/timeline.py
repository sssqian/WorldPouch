"""
时间轴组件 — 从后端 timeline API 获取数据，按章节分组展示事件流。

运行原理：
1. 当用户打开章节时，后端自动调用 AI 解析（见 chapter_reader 的 _trigger_parse）
2. 解析结果写入 timeline.json，包含：人物登场、地点解锁、关键事件
3. 本组件从 GET /api/novels/{name}/timeline 拉取数据并渲染
"""

from __future__ import annotations

import streamlit as st
import httpx

API_BASE_URL = "http://localhost:8001"

EVENT_TYPE_ICONS = {
    "character_intro": "👤",
    "location_unlock": "📍",
    "epic_event": "⚡",
    "relationship_change": "🔗",
}


def render_timeline() -> None:
    """拉取并渲染章节时间轴。"""
    novel_name: str | None = st.session_state.get("current_novel")
    if not novel_name:
        st.info("请先选择小说。")
        return

    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=15) as client:
            response = client.get(f"/api/novels/{novel_name}/timeline")
    except httpx.ConnectError:
        st.warning("无法连接后端。")
        return

    if response.status_code != 200:
        st.error(f"获取时间轴失败：{response.status_code}")
        return

    data = response.json()
    chapters: list[dict] = data.get("chapters", [])

    if not chapters:
        st.info(
            "时间轴为空 — 阅读章节后将自动触发 AI 解析。\n\n"
            "解析后的数据包括：人物登场、新地点解锁、关键情节事件。"
        )
        return

    st.caption(f"已解析 {len(chapters)} 章 · 共 {sum(len(ch.get('events', [])) for ch in chapters)} 个事件")

    # 固定高度滚动容器
    with st.container(height=480, border=False):
        for ch in chapters:
            ch_id = ch.get("chapter_id", "?")
            ch_title = ch.get("chapter_title", "")
            events = ch.get("events", [])

            if not events:
                continue

            st.markdown(f"**第{ch_id}章** {ch_title}")
            for ev in events:
                icon = EVENT_TYPE_ICONS.get(ev.get("event_type", ""), "📌")
                desc = ev.get("description", "")
                st.caption(f"{icon} {desc}")
            st.divider()
