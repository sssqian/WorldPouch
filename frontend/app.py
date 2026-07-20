"""
Streamlit 主入口 — 小说视觉化阅读助手前端。

启动方式：streamlit run frontend/app.py
"""

from __future__ import annotations

import streamlit as st

from frontend.components.character_panel import render_character_panel
from frontend.components.chapter_reader import render_chapter_reader
from frontend.components.novel_importer import render_import_form, render_imported_novels
from frontend.components.relationship_graph import render_relationship_graph
from frontend.components.timeline import render_timeline

# ── 页面配置 ──────────────────────────────────────────────
st.set_page_config(
    page_title="小说视觉化阅读助手",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 全局 CSS ────────────────────────────────────────────
st.markdown("""
<style>
    /* 侧边栏宽度 */
    section[data-testid="stSidebar"] {
        min-width: 400px !important;
    }
    /* 侧边栏按钮：禁止文字竖向排列，保持在水平方向 */
    section[data-testid="stSidebar"] .stButton > button {
        white-space: nowrap;
        padding: 0.3rem 0.5rem;
        font-size: 0.82rem;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        font-size: 0.85rem;
    }
    /* 消除侧边栏内所有容器内边距，让章节目录框撑满侧边栏宽度 */
    section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderless"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
        width: 100% !important;
        max-width: 100% !important;
        overflow-x: visible !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        padding-left: 0 !important;
        padding-right: 0 !important;
        overflow-x: visible !important;
    }
    /* 侧边栏主内容区去除右侧留白 */
    section[data-testid="stSidebar"] > div:first-child {
        padding-right: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 会话状态初始化 ─────────────────────────────────────
if "current_novel" not in st.session_state:
    st.session_state.current_novel = None
if "current_chapter" not in st.session_state:
    st.session_state.current_chapter = 1

# ── 侧边栏 ──────────────────────────────────────────────
with st.sidebar:
    st.title("📖 小说视觉化阅读助手")
    st.markdown("以章节为时间轴的动态小说沙盒")
    st.divider()

    # 已导入的小说列表
    render_imported_novels()

# ── 主页面 ──────────────────────────────────────────────
current_novel: str | None = st.session_state.current_novel

if current_novel:
    # ── 阅读模式 ──
    st.title(f"📖 {current_novel}")
    col_left, col_right = st.columns([7, 3])

    with col_left:
        render_chapter_reader()

    with col_right:
        tab1, tab2, tab3 = st.tabs(["🎴 人物卡", "🕸️ 关系网", "📋 时间轴"])

        with tab1:
            render_character_panel()

        with tab2:
            render_relationship_graph()

        with tab3:
            render_timeline()
else:
    # ── 导入模式 ──
    st.title("🗺️ 世界浓缩文件夹导入")

    render_import_form()

    st.divider()
    st.markdown(
        "💡 **提示**：导入后会自动创建以下目录结构：\n\n"
        "```\n"
        "data/novels/{小说名}_world/\n"
        "├── {小说名}.txt           # 原始小说文本\n"
        "├── world_metadata.json    # 核心元数据\n"
        "├── timeline.json          # 章节时间轴数据\n"
        "├── chapters.json          # 章节索引\n"
        "└── assets/                # 静态资源\n"
        "    ├── characters/        # 人物头像\n"
        "    ├── maps/              # 场景地图\n"
        "    └── events/            # 事件插画\n"
        "```"
    )

    # 返回导入页面的按钮（阅读模式下在侧边栏显示）
    if st.sidebar.button("← 返回导入页面", use_container_width=True):
        st.session_state.current_novel = None
        st.rerun()
