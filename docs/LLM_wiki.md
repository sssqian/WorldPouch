# 项目核心知识库 (LLM WIKI)

本文档与代码保持 100% 同步。任何对 `models/`、`api/`、`data/novels/` 的修改都必须同步更新本文档。

---

## 一、data/novels/ 文件夹物理结构

```
data/novels/{novel_name}_world/          # 世界浓缩文件夹根目录
├── {novel_name}.txt                     # 原始小说文本（导入时保存的副本）
├── world_metadata.json                  # 核心元数据
├── timeline.json                        # 章节时间轴数据（AI 解析结果）
├── chapters.json                        # 章节索引（切分结果）
└── assets/                              # 静态资源
    ├── characters/                      # 人物头像与插图
    ├── maps/                            # 大地图及地标场景图
    └── events/                          # 章节高潮事件插画
```

---

## 二、Pydantic 模型 (backend/app/models/world_models.py)

### WorldMetadata — world_metadata.json

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `current_chapter` | `int` | 当前阅读进度（章节号，默认 0） |
| `total_chapters` | `int` | 总章节数 |
| `art_style` | `ArtStyle` | 全局画风配置 |
| `created_at` | `str` | 创建时间 (ISO 8601) |
| `updated_at` | `str` | 最后更新时间 (ISO 8601) |

### ArtStyle

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `style` | `str` | `"国风动漫"` | 写实风格 / 国风动漫 / 玄幻3D |
| `character_style` | `str` | `"anime"` | 人物画风标识 |
| `background_style` | `str` | `"landscape"` | 背景画风标识 |

### TimelineData — timeline.json

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `chapters` | `list[ChapterTimeline]` | 所有章节的时间轴条目 |

### ChapterTimeline

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter_id` | `int` | 章节号 |
| `chapter_title` | `str` | 章节标题 |
| `events` | `list[TimelineEvent]` | 本章事件列表 |
| `unlocked_locations` | `list[str]` | 新解锁地点 |
| `changed_relationships` | `list[str]` | 关系变化描述 |

### TimelineEvent

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter_id` | `int` | 事件发生章节 |
| `event_type` | `str` | 类型：character_intro / location_unlock / relationship_change / epic_event |
| `description` | `str` | 事件描述 |
| `related_entities` | `list[str]` | 关联实体名称 |

### ChapterIndex — chapters.json

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `chapters` | `list[ChapterItem]` | 章节索引条目 |

### ChapterItem

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `int` | 章节序号（从 1 开始） |
| `title` | `str` | 章节标题，如「第一章 陨落的天才」 |
| `start_line` | `int` | 在原始 TXT 中的起始行号（0-based） |
| `end_line` | `int` | 在原始 TXT 中的结束行号（不含，0-based） |

### ChapterContent — API 响应

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `chapter_id` | `int` | 章节序号 |
| `chapter_title` | `str` | 章节标题 |
| `content` | `str` | 章节正文 |
| `total_chapters` | `int` | 全书总章数 |

### Character — AI 解析人物

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 人物姓名 |
| `description` | `str` | 身份/外貌简述 |
| `relation_to_mc` | `str` | 与主角的关系 |

### Location — AI 解析地点

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 地点名称 |
| `description` | `str` | 地点描述 |

### ChapterParseResult — AI 解析单章输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter_id` | `int` | 章节号 |
| `summary` | `str` | 核心剧情摘要（≤100字） |
| `characters` | `list[Character]` | 本章出场/关系变化的人物 |
| `locations` | `list[Location]` | 本章出现的新地点 |
| `key_events` | `list[str]` | 本章关键事件列表 |

### ParseResponse — 解析请求响应

| 字段 | 类型 | 说明 |
|------|------|------|
| `chapter_id` | `int` | 已解析的章节号 |
| `parse_result` | `ChapterParseResult` | 解析结果 |
| `from_cache` | `bool` | 是否来自缓存（避免重复 LLM 调用） |

### CharacterListResponse — 人物列表

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `characters` | `list[Character]` | 已解锁人物（跨章去重） |

### RelationshipEdge — 关系边

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | `str` | 人物A |
| `target` | `str` | 人物B |
| `relation` | `str` | 关系描述 |

### RelationshipGraph — 关系网

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `nodes` | `list[str]` | 所有人物节点名 |
| `edges` | `list[RelationshipEdge]` | 关系边列表 |

### ImportNovelResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| `novel_name` | `str` | 小说名称 |
| `world_dir` | `str` | 世界文件夹路径 |
| `metadata_path` | `str` | 元数据文件路径 |
| `timeline_path` | `str` | 时间轴文件路径 |
| `assets_dir` | `str` | 资源文件夹路径 |
| `chapters_path` | `str` | 章节索引文件路径 |
| `message` | `str` | 导入结果消息 |

---

## 三、API 接口契约 (backend/app/api/routes/novel.py)

Base URL: `http://localhost:8000`

### POST /api/novels/import

上传 TXT 小说，自动创建世界浓缩文件夹 + 章节切分。

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `file` | `UploadFile` | form | .txt 小说文件 |
| `novel_name` | `str?` | query | 可选，不传则取文件名 |

Response: `ImportNovelResponse`

### GET /api/novels/list

列出已导入的小说名称。

Response: `list[str]`

### GET /api/novels/{novel_name}/metadata

获取小说的核心元数据。

Response: `WorldMetadata`

### GET /api/novels/{novel_name}/timeline

获取章节时间轴数据。

Response: `TimelineData`

### GET /api/novels/{novel_name}/chapters

获取章节索引（标题 + 行号）。

Response: `ChapterIndex`

### GET /api/novels/{novel_name}/chapter/{chapter_id}

获取指定章节的正文内容。

| 参数 | 类型 | 位置 | 说明 |
|------|------|------|------|
| `novel_name` | `str` | path | 小说名称 |
| `chapter_id` | `int` | path | 章节号（从 1 开始） |

Response: `ChapterContent`

### POST /api/novels/{novel_name}/parse/{chapter_id}

触发 AI 解析指定章节，结果写入 timeline.json。已解析过的章节从缓存返回。

Response: `ParseResponse`

### GET /api/novels/{novel_name}/characters

获取已解锁人物列表（从 timeline 跨章聚合去重）。

Response: `CharacterListResponse`

### GET /api/novels/{novel_name}/relationships

获取当前人物关系网（节点 + 边）。

Response: `RelationshipGraph`

---

## 四、服务层 (backend/app/services/)

### novel_importer.py

| 函数 | 说明 |
|------|------|
| `create_world_directory(txt_path, novel_name)` | 创建世界文件夹 + 章节切分 |
| `load_world_metadata(novel_name)` | 加载元数据 → `WorldMetadata` |
| `load_timeline(novel_name)` | 加载时间轴 → `TimelineData` |
| `list_imported_novels()` | 扫描已导入小说列表 |
| `get_world_dir(novel_name)` | 获取世界文件夹根路径 |
| `get_chapters_index_path(novel_name)` | 获取 chapters.json 路径 |
| `get_original_txt_path(novel_name)` | 获取原始 TXT 路径 |
| `get_chapter(novel_name, chapter_id)` | **便捷查询**：小说名+章节号 → `ChapterContent` |

### chapter_splitter.py

| 函数 | 说明 |
|------|------|
| `split_chapters(txt_path)` | 扫描并按章节标题切分 → `ChapterIndex` |
| `get_chapter_content(txt_path, chapter_item)` | 按索引读取章节正文 |
| `save_chapter_index(index, output_path)` | 写入 chapters.json |
| `load_chapter_index(json_path)` | 从 chapters.json 加载 |

章节标题匹配正则：`^\s*第[\u4e00-\u9fff\d零一二三四五六七八九十百千万]+[章回节卷].*$`

### chapter_parser.py

| 函数 | 说明 |
|------|------|
| `parse_chapter(novel_name, chapter_id, title, content, timeline_path)` | 异步解析单章 → LLM 提取人物/地点/事件 → 写入 timeline.json |
| `get_characters(novel_name, timeline_path)` | 从 timeline 聚合去重人物列表 |
| `get_relationships(novel_name, timeline_path)` | 从 timeline 构建关系网 |

### core/config.py

| 属性 | 环境变量 | 默认值 |
|------|------|------|
| `settings.llm_api_key` | `LLM_API_KEY` | `""` |
| `settings.llm_base_url` | `LLM_BASE_URL` | `https://api.deepseek.com/v1` |
| `settings.llm_model` | `LLM_MODEL` | `deepseek-chat` |
| `settings.llm_max_retries` | `LLM_MAX_RETRIES` | `3` |

### core/llm_client.py

| 函数 | 说明 |
|------|------|
| `structured_completion(prompt, response_model)` | Instructor 封装：发送 prompt → 返回强类型 Pydantic 对象 |
