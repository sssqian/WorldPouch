"""
关系网可视化组件 — 使用 pyvis 渲染交互式力导向图。

点击按钮后在 expander 中展开，避免页面变长。
"""

from __future__ import annotations

import streamlit as st
import httpx
from pyvis.network import Network

API_BASE_URL = "http://localhost:8001"


def render_relationship_graph() -> None:
    """以按钮+expander模式展示关系网。"""
    novel_name: str | None = st.session_state.get("current_novel")
    if not novel_name:
        st.info("请先选择小说。")
        return

    # ── 切换按钮 ──
    show_key = f"show_graph_{novel_name}"
    if st.button(
        "🕸️ 展开人物关系网",
        key=f"toggle_graph_{novel_name}",
        use_container_width=True,
    ):
        st.session_state[show_key] = not st.session_state.get(show_key, False)

    if not st.session_state.get(show_key):
        return

    # ── 加载数据 ──
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=15) as client:
            response = client.get(f"/api/novels/{novel_name}/relationships")
    except httpx.ConnectError:
        st.warning("无法连接后端。")
        return

    if response.status_code != 200:
        st.error(f"获取关系数据失败：{response.status_code}")
        return

    data = response.json()
    nodes: list[str] = data.get("nodes", [])
    edges: list[dict] = data.get("edges", [])

    if not nodes or len(nodes) <= 1:
        st.info("暂未解析任何人物关系。阅读章节后将自动 AI 解析。")
        return

    st.caption(f"已解锁 {len(nodes)} 个人物，{len(edges)} 条关系")

    # ── 构建 pyvis 网络图 ──
    net = Network(
        height="450px", width="100%", directed=False,
        bgcolor="#ffffff", font_color="#333333",
    )

    for name in nodes:
        title = _build_node_title(name, edges)
        net.add_node(name, label=name, title=title, size=22)

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        rel = edge.get("relation", "")
        net.add_edge(src, tgt, title=rel, label=rel, width=2, arrows="to")

    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "stabilization": {"iterations": 100},
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 180,
          "springConstant": 0.04,
          "damping": 0.5
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "zoomView": true,
        "dragView": true
      },
      "edges": {
        "smooth": {"type": "continuous"}
      }
    }
    """)

    html = net.generate_html()
    st.components.v1.html(html, height=500, scrolling=False)


def _build_node_title(name: str, edges: list[dict]) -> str:
    """生成节点悬停 tooltip — 展示该人物的所有关系。"""
    related: list[str] = []
    for e in edges:
        if e["source"] == name and e.get("target"):
            rel = e.get("relation", "")
            related.append(f"→ {e['target']} ({rel})" if rel else f"→ {e['target']}")
        elif e["target"] == name and e.get("source"):
            rel = e.get("relation", "")
            related.append(f"← {e['source']} ({rel})" if rel else f"← {e['source']}")
    if related:
        return f"<b>{name}</b><br>" + "<br>".join(related[:10])
    return f"<b>{name}</b>"
