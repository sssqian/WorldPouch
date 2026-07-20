"""
人物卡面板 Streamlit 组件。

右侧栏 tabs 中的「人物卡」Tab，展示当前已解锁的所有人物。
"""

from __future__ import annotations

import streamlit as st
import httpx

API_BASE_URL = "http://localhost:8001"


def render_character_panel() -> None:
    """拉取并渲染人物卡片列表。"""
    novel_name: str | None = st.session_state.get("current_novel")
    if not novel_name:
        st.info("请先选择小说。")
        return

    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=15) as client:
            response = client.get(f"/api/novels/{novel_name}/characters")
    except httpx.ConnectError:
        st.warning("无法连接后端。")
        return

    if response.status_code != 200:
        st.error(f"获取人物列表失败：{response.status_code}")
        return

    characters: list[dict] = response.json().get("characters", [])

    if not characters:
        st.info("暂未解析任何人物。阅读章节后将自动 AI 解析。")
        return

    st.caption(f"已解锁 {len(characters)} 位人物")

    # 固定高度滚动容器，人物增多不撑长网页
    with st.container(height=480, border=False):
        for ch in characters:
            _render_character_card(ch)


def _render_character_card(ch: dict) -> None:
    """渲染单张人物卡片。"""
    with st.container(border=True):
        st.markdown(f"**{ch['name']}**")
        # 从描述中提取主要信息
        desc = ch.get("description", "")
        if desc:
            st.caption(desc[:120])
        relation = ch.get("relation_to_mc", "")
        if relation:
            st.caption(f"与主角关系：{relation}")
