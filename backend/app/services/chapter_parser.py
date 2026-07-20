"""
AI 章节解析服务。

将章节正文发送给大模型，提取人物、地点、关系、关键事件，
并将解析结果写入 timeline.json 实现跨章累积。

缓存机制：已在 timeline.json 中存在的 chapter_id 不会重复解析。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from backend.app.core.llm_client import structured_completion
from backend.app.models.world_models import (
    ChapterParseResult,
    ChapterTimeline,
    Character,
    CharacterListResponse,
    Location,
    ParseResponse,
    RelationshipEdge,
    RelationshipGraph,
    TimelineData,
    TimelineEvent,
)

logger = logging.getLogger(__name__)

# 解析单章的 Prompt 模板
PARSE_PROMPT_TEMPLATE = """请分析以下小说章节内容，提取结构化信息。

**章节标题**：{chapter_title}
**章节正文**：
{chapter_content}

{known_characters_context}
请严格按以下字段提取：
1. summary：本章核心剧情摘要（不超过100字）。
2. characters：本章**新出场**或**与主角发生关系变化**的人物。
   - name: 人物姓名
   - description: 身份/外貌简述（如"萧家三少爷，15岁，面容清秀"）
   - relation_to_mc: 该人物与主角的关系（如"父亲"、"青梅竹马"、"初次见面的敌人"）
3. locations：本章**首次出现**的新地点。
   - name: 地点名称
   - description: 地点描述（如"萧家演武场，位于家族大院中央"）
4. key_events：本章发生的核心事件列表（每项一句话，如"萧炎在演武场当众测试斗气"）。

**【人物合并规则】-- 请严格遵守！**
- 如果本章中某个角色在"已出场人物列表"中已被记载，请不要再次作为新人物提取。
- 如果本章揭示了一个已出场代称人物的真名（例如：之前叫"白袍少女"，本章揭晓她叫"纳兰嫣然"），请使用真名作为 name，并在 description 中注明"前称：白袍少女"。
- 对于已出场人物，仅在该人物**关系发生变化**时才再次列出。
"""


def _build_known_characters_context(timeline: TimelineData) -> str:
    """从已有 timeline 中提取已知人物列表，构建 prompt 上下文。"""
    names: list[str] = []
    seen: set[str] = set()
    for ch in timeline.chapters:
        for ev in ch.events:
            if ev.event_type == "character_intro" and ev.related_entities:
                name = ev.related_entities[0]
                if name not in seen:
                    seen.add(name)
                    names.append(f"- {name}（{ev.description}）")

    if not names:
        return ""

    return (
        "**已出场人物列表（请勿重复提取，若揭示真名请用真名+注明前称）：**\n"
        + "\n".join(names)
        + "\n\n"
    )


def _parse_result_to_timeline(result: ChapterParseResult) -> ChapterTimeline:
    """将解析结果转换为 timeline 条目。"""
    events: list[TimelineEvent] = []

    for ch in result.characters:
        events.append(
            TimelineEvent(
                chapter_id=result.chapter_id,
                event_type="character_intro",
                description=f"人物登场：{ch.name}（{ch.description}），关系：{ch.relation_to_mc}",
                related_entities=[ch.name],
            )
        )
    for loc in result.locations:
        events.append(
            TimelineEvent(
                chapter_id=result.chapter_id,
                event_type="location_unlock",
                description=f"新地点解锁：{loc.name}（{loc.description}）",
                related_entities=[loc.name],
            )
        )
    for event_desc in result.key_events:
        events.append(
            TimelineEvent(
                chapter_id=result.chapter_id,
                event_type="epic_event",
                description=event_desc,
                related_entities=[],
            )
        )

    return ChapterTimeline(
        chapter_id=result.chapter_id,
        chapter_title="",
        events=events,
        unlocked_locations=[loc.name for loc in result.locations],
        changed_relationships=[
            f"{ch.name} → {ch.relation_to_mc}" for ch in result.characters
        ],
    )


async def parse_chapter(
    novel_name: str,
    chapter_id: int,
    chapter_title: str,
    chapter_content: str,
    timeline_path: Path,
) -> ParseResponse:
    """
    解析单章内容，将结果写入 timeline.json。

    如果本章已被解析过（timeline 中已有该 chapter_id），直接返回缓存。

    Args:
        novel_name: 小说名称。
        chapter_id: 章节号。
        chapter_title: 章节标题。
        chapter_content: 章节正文。
        timeline_path: timeline.json 文件路径。

    Returns:
        ParseResponse: 含解析结果和是否来自缓存。
    """
    # ── 缓存检查 ──
    existing_timeline: TimelineData
    if timeline_path.exists():
        with open(timeline_path, encoding="utf-8") as f:
            data = json.load(f)
        existing_timeline = TimelineData(**data)

        for ch in existing_timeline.chapters:
            if ch.chapter_id == chapter_id:
                # 从已有 timeline 条目反向重建 ChapterParseResult
                characters: list[Character] = []
                locations: list[Location] = []
                key_events: list[str] = []

                for ev in ch.events:
                    if ev.event_type == "character_intro":
                        # 从 description 中提取（简化：只用实体名作为描述）
                        characters.append(
                            Character(
                                name=ev.related_entities[0] if ev.related_entities else "未知",
                                description=ev.description,
                                relation_to_mc="",
                            )
                        )
                    elif ev.event_type == "location_unlock":
                        locations.append(
                            Location(
                                name=ev.related_entities[0] if ev.related_entities else "未知",
                                description=ev.description,
                            )
                        )
                    elif ev.event_type == "epic_event":
                        key_events.append(ev.description)

                cached_result = ChapterParseResult(
                    chapter_id=chapter_id,
                    summary=ev.description if ch.events else "",
                    characters=characters,
                    locations=locations,
                    key_events=key_events,
                )
                return ParseResponse(
                    chapter_id=chapter_id,
                    parse_result=cached_result,
                    from_cache=True,
                )
    else:
        existing_timeline = TimelineData(novel_name=novel_name)

    # ── LLM 调用 ──
    known_characters_context = _build_known_characters_context(existing_timeline)
    prompt = PARSE_PROMPT_TEMPLATE.format(
        chapter_title=chapter_title,
        chapter_content=chapter_content[:6000],  # 截断长章节，避免 token 超限
        known_characters_context=known_characters_context,
    )

    result = await structured_completion(
        prompt=prompt,
        response_model=ChapterParseResult,
        system_message="你是专业的小说内容分析助手，严格按 JSON Schema 返回结构化数据。",
    )
    # 确保 chapter_id 正确
    result.chapter_id = chapter_id

    # ── 写入 timeline ──
    timeline_entry = _parse_result_to_timeline(result)
    timeline_entry.chapter_title = chapter_title

    # 移除已有同章节条目后插入
    existing_timeline.chapters = [
        ch for ch in existing_timeline.chapters if ch.chapter_id != chapter_id
    ]
    existing_timeline.chapters.append(timeline_entry)
    existing_timeline.chapters.sort(key=lambda c: c.chapter_id)

    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(existing_timeline.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    return ParseResponse(
        chapter_id=chapter_id,
        parse_result=result,
        from_cache=False,
    )


def get_characters(novel_name: str, timeline_path: Path) -> CharacterListResponse:
    """从 timeline.json 聚合所有已解锁人物（去重），自动剔除被真名合并的旧代称。"""
    if not timeline_path.exists():
        return CharacterListResponse(novel_name=novel_name, characters=[])

    with open(timeline_path, encoding="utf-8") as f:
        timeline = TimelineData(**json.load(f))

    # 第一遍：收集所有旧代称（被"前称"标记的名字）
    old_names: set[str] = set()
    for ch in timeline.chapters:
        for ev in ch.events:
            if ev.event_type == "character_intro":
                # 解析 description 中的"前称：XXX"
                m = re.search(r"前称[：:]\s*([^）)]+?)(?:[），\)]|$)", ev.description)
                if m:
                    old_name = m.group(1).strip()
                    if old_name:
                        old_names.add(old_name)

    # 第二遍：构建人物列表，剔除旧代称
    seen: set[str] = set()
    characters: list[Character] = []

    for ch in timeline.chapters:
        for ev in ch.events:
            if ev.event_type == "character_intro" and ev.related_entities:
                name = ev.related_entities[0]
                # 如果这个名字是某个真名角色的"前称"，跳过
                if name in old_names:
                    continue
                if name not in seen:
                    seen.add(name)
                    characters.append(
                        Character(
                            name=name,
                            description=ev.description,
                            relation_to_mc="",
                        )
                    )

    return CharacterListResponse(novel_name=novel_name, characters=characters)


def get_relationships(novel_name: str, timeline_path: Path) -> RelationshipGraph:
    """从 timeline.json 构建关系网（节点 + 边），自动剔除旧代称。"""
    if not timeline_path.exists():
        return RelationshipGraph(novel_name=novel_name)

    with open(timeline_path, encoding="utf-8") as f:
        timeline = TimelineData(**json.load(f))

    # 收集旧代称
    old_names: set[str] = set()
    for ch in timeline.chapters:
        for ev in ch.events:
            if ev.event_type == "character_intro":
                m = re.search(r"前称[：:]\s*([^）)]+?)(?:[），\)]|$)", ev.description)
                if m and m.group(1).strip():
                    old_names.add(m.group(1).strip())

    nodes: set[str] = {"主角"}
    edges: list[RelationshipEdge] = []

    for ch in timeline.chapters:
        chars_in_chapter: list[str] = []
        for ev in ch.events:
            if ev.event_type == "character_intro" and ev.related_entities:
                name = ev.related_entities[0]
                if name not in old_names:
                    nodes.add(name)
                    chars_in_chapter.append(name)

        # 为本章人物与主角建立边
        for rel in ch.changed_relationships:
            if "→" in rel:
                parts = rel.split("→", 1)
                source = parts[0].strip()
                relation = parts[1].strip() if len(parts) > 1 else ""
                edges.append(
                    RelationshipEdge(
                        source=source,
                        target="主角",  # 所有关系以主角为中心
                        relation=relation,
                    )
                )
                nodes.add(source)

    # 去重边
    unique_edges: list[RelationshipEdge] = []
    seen_edges: set[str] = set()
    for e in edges:
        key = f"{e.source}-{e.target}-{e.relation}"
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    return RelationshipGraph(
        novel_name=novel_name,
        nodes=sorted(nodes),
        edges=unique_edges,
    )
