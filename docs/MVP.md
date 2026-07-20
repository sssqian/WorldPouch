# 小说视觉化阅读助手 — 最简 MVP 方案

## 一、MVP 目标

**一句话定义**：导入一本 TXT 小说 → 逐章阅读 → AI 自动提取人物/关系/地点 → 页面实时展示人物卡和关系网。

验证的核心假设：用户是否愿意为「边读小说边看人物关系图」这种体验买单？

---

## 二、MVP 范围：做什么 / 不做什么

### 要做（P0）

| 模块 | 功能 | 验收标准 |
|------|------|----------|
| 小说导入 | 上传 TXT，自动建世界浓缩文件夹 | 上传后 data/novels/ 下出现 `{书名}_world/` 完整目录 |
| 章节切分 | 按「第X章」自动切分全文 | 时间轴显示总章节数，支持跳转任意章 |
| 章节阅读器 | 左侧阅读区展示当前章正文 | 支持上一章/下一章切换，当前章号同步更新 |
| AI 章节解析 | 每进入一章，LLM 提取人物、关系、地点 | 返回结构化 JSON（Pydantic 校验），写入 timeline.json |
| 人物卡面板 | 右侧展示本章出场人物卡片 | 卡片含姓名、描述、关系标签；跨章累积去重 |
| 关系网 | 用 pyvis 渲染当前已解锁的人物关系图 | 节点可拖拽，连线标关系 |

### 不做（P1/P2）

- 图片生成（人物头像、场景 CG、事件插画）— 成本高，MVP 用纯文字卡片替代
- 动态大地图 — 先用关系网替代空间表达
- 剧情变量模拟器（蝴蝶效应分支推演）— 进阶功能，MVP 不做
- 多画风切换 — 等有生图能力后再加
- 外貌特征 IP 锁定（Reference Image）— 依赖生图

---

## 三、MVP 用户流程

```
[用户打开页面]
      │
      ▼
[侧边栏：上传 TXT] ──→ 后端自动创建 world 目录 ──→ 侧边栏显示「斗破苍穹」
      │
      ▼
[点击「斗破苍穹」进入阅读]
      │
      ├── 左侧 70%：章节正文阅读区
      │     ├── 标题：第1章 陨落的天才
      │     ├── 正文滚动区域
      │     └── 「上一章」「下一章」按钮
      │
      └── 右侧 30%：可视化面板 (tabs)
            ├── Tab 1「人物卡」：当前已解锁人物列表
            ├── Tab 2「关系网」：pyvis 力导向图
            └── Tab 3「时间轴」：已解析章节事件列表
```

---

## 四、待开发的 P0 任务清单

### 4.1 章节切分服务 `backend/app/services/chapter_splitter.py`  ✅ 已完成

```
输入：TXT 文件路径
输出：{chapter_id, chapter_title, content} 列表
实现：
  - 正则匹配「第X章 标题」或「第X回 标题」
  - 返回有序列表，写入 chapters.json（可选）
  - 提供 get_chapter(novel_name, chapter_id) 查询函数
```

### 4.2 AI 章节解析服务 `backend/app/services/chapter_parser.py`  ✅ 已完成

```
输入：章节目录 + 章节正文
输出：ChapterData（Pydantic 模型）
实现：
  - 使用 Instructor + DeepSeek/OpenAI API
  - Prompt 模板：提取人物(name/描述/关系)、新地点、摘要
  - 解析结果追加写入 timeline.json
  - 对已解析章节做缓存，避免重复调用
```

需要的 Pydantic 模型（新增或扩展现有 `world_models.py`）：

```python
class Character(BaseModel):
    name: str
    description: str  # 身份/外貌简述
    relation_to_mc: str  # 与主角关系

class Location(BaseModel):
    name: str
    description: str

class ChapterParseResult(BaseModel):
    chapter_id: int
    summary: str  # ≤100字
    characters: list[Character]
    locations: list[Location]
    key_events: list[str]
```

### 4.3 LLM 客户端配置 `backend/app/core/llm_client.py`  ✅ 已完成

```
封装 Instructor + OpenAI/DeepSeek 调用
  - 支持 API Key 环境变量配置
  - 统一错误重试（3次）
  - 支持异步调用（httpx）
```

### 4.4 后端 API 新增

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/novels/{name}/chapter/{id}` | 获取指定章节正文 ✅ |
| `POST` | `/api/novels/{name}/parse/{id}` | 触发 AI 解析某一章 ✅ |
| `GET` | `/api/novels/{name}/characters` | 获取已解锁人物列表 ✅ |
| `GET` | `/api/novels/{name}/relationships` | 获取当前关系图数据 ✅ |

### 4.5 前端改造 `frontend/app.py`  ✅ 已完成

```
选择小说后进入「阅读模式」：
  - st.session_state.current_novel, current_chapter
  - st.columns([7, 3]) 左右分栏
  - 左栏：章节正文阅读 + 章节导航
  - 右栏：st.tabs(["人物卡", "关系网", "时间轴"])
```

### 4.6 关系网组件 `frontend/components/relationship_graph.py`  ✅ 已完成

```
使用 streamlit.components.v1.html + pyvis 渲染
  - 从后端 GET /relationships 获取节点/边数据
  - 嵌入 iframe 展示交互式力导向图
```

---

## 五、技术风险与对策

| 风险 | 对策 |
|------|------|
| LLM API 调用慢（每章 3-10s） | 后台异步解析 + st.spinner；已解析章走缓存 |
| LLM 输出格式不稳定 | Instructor + Pydantic 强制校验，失败自动重试 |
| 长篇小说章节过多（1000+章） | 前端分页 + 按需加载；只解析用户读到的章 |
| pyvis 在 Streamlit 中渲染卡顿 | 限制展示节点数（默认150个）；超过时用筛选 |
| DeepSeek API 额度不足 | 支持配置 API Key，也支持 Ollama 本地模型降级 |

---

## 六、不做的理由（P1 延后说明）

| 延后项 | 理由 |
|--------|------|
| 图片生成（头像/场景/事件 CG） | MVP 阶段用文字卡片即可验证「视觉化阅读」价值；生图 API 成本高且慢 |
| 动态大地图 | 关系网已承载「人物-空间」连接；地图需要自建坐标系统，ROI 不够 |
| 剧情变量模拟器 | 完全属于差异化进阶功能，基础体验没跑通前不做 |
| 多小说聚合对比 | MVP 先做到「一本小说」的闭环 |

---

## 七、里程碑

| 里程碑 | 内容 | 交付物 |
|--------|------|--------|
| M1 · 脚手架 | 项目骨架 + 导入 + 目录创建 | `✅ 已完成` |
| M2 · 可读 | 章节切分 + 阅读器页面 | `✅ 已完成` |
| M3 · 可解析 | AI 解析单章 + 人物卡展示 | `✅ 已完成` |
| M4 · 可联网 | 关系网 + 多章累积 | `✅ 已完成` |
| **M5 · MVP 发布** | 端到端闭环：读 → 解析 → 可视化 | `✅ 已完成` |
