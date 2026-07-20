"""
小说导入 Streamlit 组件。

提供 TXT 文件上传、目录结构预览、导入状态展示的 UI。
"""

from __future__ import annotations

import streamlit as st
import httpx

API_BASE_URL = "http://localhost:8001"


def render_import_form() -> None:
    """渲染小说导入表单。"""
    st.subheader("📥 导入 TXT 小说")

    with st.form("novel_import_form", clear_on_submit=True):
        novel_name = st.text_input(
            "小说名称（可选）",
            placeholder="留空则自动使用文件名",
            help="例如：斗破苍穹",
        )
        uploaded_file = st.file_uploader(
            "选择 TXT 小说文件",
            type=["txt"],
            help="支持 .txt 格式的小说文本文件",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("导入", type="primary", use_container_width=True)

    if submitted and uploaded_file is not None:
        _handle_import(uploaded_file, novel_name or None)
    elif submitted:
        st.warning("请先选择一个 TXT 文件。")


def _handle_import(uploaded_file, novel_name: str | None) -> None:
    """处理导入请求并展示结果。"""
    with st.spinner("正在创建世界浓缩文件夹..."):
        try:
            with httpx.Client(base_url=API_BASE_URL, timeout=60) as client:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/plain")}
                params = {}
                if novel_name:
                    params["novel_name"] = novel_name

                response = client.post("/api/novels/import", files=files, params=params)

            if response.status_code == 200:
                result = response.json()
                _show_success_result(result)
            else:
                detail = response.json().get("detail", "未知错误")
                st.error(f"导入失败：{detail}")

        except httpx.ConnectError:
            st.error(
                "无法连接后端服务。请确认 FastAPI 服务已启动：\n\n"
                "```bash\nuvicorn backend.app.main:app --reload\n```"
            )
        except Exception as e:
            st.error(f"导入过程发生异常：{e}")


def _show_success_result(result: dict) -> None:
    """展示导入成功后的目录结构。"""
    st.success(result["message"])

    with st.expander("📂 世界浓缩文件夹目录结构", expanded=True):
        novel_name = result["novel_name"]
        world_dir = f"data/novels/{novel_name}_world/"

        st.markdown(f"**`{world_dir}`**  # “世界浓缩文件夹”根目录")

        lines = [
            (" ├── world_metadata.json", "1. 核心元数据", result["metadata_path"]),
            (" ├── timeline.json", "2. 章节时间轴数据", result["timeline_path"]),
            (" ├── assets/", "3. 静态资源文件夹", result["assets_dir"]),
            (" │   ├── characters/", "人物头像与插图", result["characters_dir"]),
            (" │   ├── maps/", "大地图及地标场景图", result["maps_dir"]),
            (" │   └── events/", "章节高潮事件插画", result["events_dir"]),
        ]

        for i, (line, desc, path) in enumerate(lines):
            if i == len(lines) - 1:
                prefix = line.replace(" ├──", " └──")
            else:
                prefix = line
            st.markdown(f"`{prefix}`  # {desc}")
            st.caption(f"路径：`{path}`")

    # 显示元数据摘要
    st.subheader("📋 元数据摘要")
    st.json(
        {
            "小说名称": result["novel_name"],
            "世界目录": result["world_dir"],
        }
    )


def render_imported_novels() -> None:
    """展示已导入的小说列表。"""
    st.subheader("📚 已导入的小说")

    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=10) as client:
            response = client.get("/api/novels/list")

        if response.status_code == 200:
            novels = response.json()
            if novels:
                for novel in novels:
                    with st.container(border=True):
                        st.markdown(f"**{novel}**")
                        # 第一行：打开阅读 + 章节列表
                        cr1, cr2 = st.columns(2)
                        with cr1:
                            if st.button(
                                "打开阅读",
                                key=f"read_{novel}",
                                use_container_width=True,
                                type="primary",
                            ):
                                st.session_state.current_novel = novel
                                st.session_state.current_chapter = 1
                                st.rerun()
                        with cr2:
                            if st.button(
                                "章节列表",
                                key=f"chlist_{novel}",
                                use_container_width=True,
                            ):
                                # 切换章节目录显示/隐藏
                                key = f"show_chapters_{novel}"
                                st.session_state[key] = not st.session_state.get(key, False)
                                st.rerun()
                        # 章节目录（在小说卡片层级渲染，不受列宽限制）
                        if st.session_state.get(f"show_chapters_{novel}"):
                            st.divider()
                            _show_chapter_list(novel)
                        # 第二行：查看元数据 + 删除
                        cr3, cr4 = st.columns([3, 1])
                        with cr3:
                            if st.button(
                                "查看元数据",
                                key=f"meta_{novel}",
                                use_container_width=True,
                            ):
                                with httpx.Client(base_url=API_BASE_URL, timeout=10) as client:
                                    resp = client.get(f"/api/novels/{novel}/metadata")
                                if resp.status_code == 200:
                                    st.json(resp.json())
                                else:
                                    st.error(f"获取元数据失败：{resp.status_code}")
                        with cr4:
                            if st.button(
                                "🗑",
                                key=f"del_{novel}",
                                use_container_width=True,
                                help=f"删除「{novel}」",
                            ):
                                st.session_state[f"confirm_del_{novel}"] = True
                                st.rerun()
                        # 删除确认
                        if st.session_state.get(f"confirm_del_{novel}"):
                            st.warning(f"确认删除「{novel}」？此操作不可恢复！")
                            col_c1, col_c2 = st.columns(2)
                            with col_c1:
                                if st.button("确认删除", key=f"confirm_yes_{novel}", type="primary"):
                                    _delete_novel(novel)
                                    st.session_state.pop(f"confirm_del_{novel}", None)
                                    st.rerun()
                            with col_c2:
                                if st.button("取消", key=f"confirm_no_{novel}"):
                                    st.session_state.pop(f"confirm_del_{novel}", None)
                                    st.rerun()
            else:
                st.info("还没有导入任何小说。请在上方导入 TXT 文件。")
        else:
            st.error(f"获取列表失败：{response.status_code}")

    except httpx.ConnectError:
        st.warning("无法连接后端服务，请确认 FastAPI 已启动。")


def _show_chapter_list(novel_name: str) -> None:
    """拉取并展示小说的章节目录。"""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=15) as client:
            response = client.get(f"/api/novels/{novel_name}/chapters")
    except httpx.ConnectError:
        st.warning("无法连接后端。")
        return

    if response.status_code != 200:
        st.error(f"获取章节列表失败：{response.status_code}")
        return

    chapters = response.json().get("chapters", [])
    if not chapters:
        st.info("未找到章节数据。")
        return

    st.markdown(f"**共 {len(chapters)} 章**")
    st.divider()

    # 固定高度滚动容器，点击标题即可跳转
    current_chapter = st.session_state.get("current_chapter")
    current_novel = st.session_state.get("current_novel")
    with st.container(height=450, border=False):
        for ch in chapters:
            ch_id = ch["id"]
            title = ch["title"]
            # 标记当前正在阅读的章节
            is_current = (current_novel == novel_name and current_chapter == ch_id)
            label = f"▸ {title}" if is_current else f"  {title}"
            if st.button(label, key=f"jump_{novel_name}_{ch_id}", use_container_width=True):
                st.session_state.current_novel = novel_name
                st.session_state.current_chapter = ch_id
                st.rerun()


def _delete_novel(novel_name: str) -> None:
    """调用后端 API 删除小说。"""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=15) as client:
            response = client.delete(f"/api/novels/{novel_name}")
        if response.status_code == 200:
            st.toast(f"「{novel_name}」已删除", icon="🗑")
            # 如果当前正在阅读该小说，清除状态
            if st.session_state.get("current_novel") == novel_name:
                st.session_state.current_novel = None
                st.session_state.current_chapter = 1
        else:
            detail = response.json().get("detail", "未知错误")
            st.error(f"删除失败：{detail}")
    except httpx.ConnectError:
        st.warning("无法连接后端，请确认 FastAPI 已启动。")
