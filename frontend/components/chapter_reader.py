"""
章节阅读器 Streamlit 组件。

提供章节正文阅读、上一章/下一章导航，按 MVP 方案放入 st.columns 的左栏。
进入新章节时自动触发 AI 解析。
"""

from __future__ import annotations

import streamlit as st
import httpx

API_BASE_URL = "http://localhost:8001"


def render_chapter_reader() -> None:
    """渲染章节正文阅读区。"""
    novel_name: str | None = st.session_state.get("current_novel")
    chapter_id: int = st.session_state.get("current_chapter", 1)

    if not novel_name:
        st.info("请先在侧边栏选择一本已导入的小说。")
        return

    # 拉取章节数据
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=30) as client:
            response = client.get(f"/api/novels/{novel_name}/chapter/{chapter_id}")
    except httpx.ConnectError:
        st.warning("无法连接后端，请确认 FastAPI 已启动。")
        return

    if response.status_code != 200:
        st.error(f"加载第{chapter_id}章失败：{response.status_code}")
        return

    data: dict = response.json()
    total: int = data["total_chapters"]

    # ── AI 解析触发（仅新章节） ──
    parsed_key = f"parsed_{novel_name}_{chapter_id}"
    if parsed_key not in st.session_state:
        _trigger_parse(novel_name, chapter_id)
        st.session_state[parsed_key] = True

    # ── 顶部导航栏 ──
    col_prev, col_title, col_next = st.columns([1, 3, 1])
    with col_prev:
        if chapter_id > 1:
            if st.button("◀ 上一章", key="prev_ch", use_container_width=True):
                st.session_state.current_chapter -= 1
                st.rerun()
        else:
            st.markdown("")  # 占位对齐
    with col_title:
        st.markdown(
            f"### {data['chapter_title']}\n"
            f"*{chapter_id} / {total} 章*"
        )
    with col_next:
        if chapter_id < total:
            if st.button("下一章 ▶", key="next_ch", use_container_width=True):
                st.session_state.current_chapter += 1
                st.rerun()

    st.divider()

    # ── 正文区域（text_area 保留原始换行，支持滚动） ──
    st.text_area(
        "正文",
        value=data["content"],
        height=500,
        label_visibility="collapsed",
        disabled=True,
    )

    # ── 底部导航 ──
    st.divider()
    col_bprev, col_btitle, col_bnext = st.columns([1, 3, 1])
    with col_bprev:
        if chapter_id > 1:
            if st.button("◀ 上一章", key="prev_ch_bot", use_container_width=True):
                st.session_state.current_chapter -= 1
                st.rerun()
    with col_bnext:
        if chapter_id < total:
            if st.button("下一章 ▶", key="next_ch_bot", use_container_width=True):
                st.session_state.current_chapter += 1
                st.rerun()

    # ── 快捷键提示 ──
    st.caption("提示：使用顶部的「上一章」「下一章」按钮无缝翻阅全书")


def _trigger_parse(novel_name: str, chapter_id: int) -> None:
    """对后端发起 AI 解析请求（异步不阻塞阅读）。"""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=90) as client:
            response = client.post(f"/api/novels/{novel_name}/parse/{chapter_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get("from_cache"):
                st.toast(f"第{chapter_id}章 已缓存，跳过解析", icon="💾")
            else:
                st.toast(f"第{chapter_id}章 AI 解析完成", icon="✅")
        else:
            detail = response.json().get("detail", "未知错误")
            st.toast(f"第{chapter_id}章 解析失败：{detail}", icon="⚠️")
    except httpx.ConnectError:
        st.toast("无法连接后端进行解析", icon="⚠️")
    except Exception as e:
        st.toast(f"解析异常：{e}", icon="⚠️")
