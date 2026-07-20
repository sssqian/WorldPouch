"""
世界浓缩文件夹的数据模型定义。

对应目录结构：
data/novels/{novel_name}_world/
├── world_metadata.json    # 核心元数据
├── timeline.json          # 章节时间轴数据
└── assets/                # 静态资源（人物头像、地图、事件插画）
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ArtStyle(BaseModel):
    """全局画风配置"""
    style: str = Field(
        default="国风动漫",
        description="画风类型：写实风格、国风动漫、玄幻3D",
    )
    character_style: str = Field(
        default="anime",
        description="人物画风标识，用于 AI 生图 prompt",
    )
    background_style: str = Field(
        default="landscape",
        description="背景画风标识，用于 AI 生图 prompt",
    )


class WorldMetadata(BaseModel):
    """核心元数据 - world_metadata.json 的结构"""
    novel_name: str = Field(..., description="小说名称")
    current_chapter: int = Field(default=0, description="当前阅读进度（章节号）")
    total_chapters: int = Field(default=0, description="总章节数")
    art_style: ArtStyle = Field(default_factory=ArtStyle, description="全局画风配置")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="世界浓缩文件夹创建时间",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="最后更新时间",
    )


class TimelineEvent(BaseModel):
    """时间轴上的单个事件"""
    chapter_id: int = Field(..., description="事件发生的章节号")
    event_type: str = Field(
        ...,
        description="事件类型：character_intro / location_unlock / relationship_change / epic_event",
    )
    description: str = Field(..., description="事件描述")
    related_entities: list[str] = Field(
        default_factory=list,
        description="关联实体名称（人物名、地名等）",
    )


class ChapterTimeline(BaseModel):
    """单个章节的时间轴条目"""
    chapter_id: int = Field(..., description="章节号")
    chapter_title: str = Field(default="", description="章节标题")
    events: list[TimelineEvent] = Field(
        default_factory=list,
        description="本章发生的事件列表",
    )
    unlocked_locations: list[str] = Field(
        default_factory=list,
        description="本章新解锁的地点",
    )
    changed_relationships: list[str] = Field(
        default_factory=list,
        description="本章发生变化的关系描述",
    )


class TimelineData(BaseModel):
    """章节时间轴数据 - timeline.json 的结构"""
    novel_name: str = Field(..., description="小说名称")
    chapters: list[ChapterTimeline] = Field(
        default_factory=list,
        description="所有章节的时间轴条目",
    )


class ChapterItem(BaseModel):
    """单章索引条目 - chapters.json 的单条记录"""
    id: int = Field(..., description="章节序号（从1开始）")
    title: str = Field(..., description="章节标题，如‘第一章 陨落的天才’")
    start_line: int = Field(..., description="在原始 TXT 中的起始行号（0-based）")
    end_line: int = Field(..., description="在原始 TXT 中的结束行号（不含，0-based）")


class ChapterIndex(BaseModel):
    """章节索引 - chapters.json 的结构"""
    novel_name: str = Field(..., description="小说名称")
    chapters: list[ChapterItem] = Field(
        default_factory=list,
        description="所有章节的索引条目",
    )


class ChapterContent(BaseModel):
    """单章正文"""
    novel_name: str = Field(..., description="小说名称")
    chapter_id: int = Field(..., description="章节序号")
    chapter_title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节正文")
    total_chapters: int = Field(..., description="全书总章数")


# ── 4.2 AI 章节解析模型 ────────────────────────────────

class Character(BaseModel):
    """单个出场人物"""
    name: str = Field(..., description="人物姓名")
    description: str = Field(..., description="身份/外貌简述")
    relation_to_mc: str = Field(..., description="与主角的关系")


class Location(BaseModel):
    """单个地点"""
    name: str = Field(..., description="地点名称")
    description: str = Field(..., description="地点描述")


class ChapterParseResult(BaseModel):
    """AI 解析单章的结构化输出"""
    chapter_id: int = Field(..., description="章节号")
    summary: str = Field(..., description="本章核心剧情摘要，不超过100字")
    characters: list[Character] = Field(default_factory=list, description="本章出场/关系变化的人物")
    locations: list[Location] = Field(default_factory=list, description="本章出现的新地点")
    key_events: list[str] = Field(default_factory=list, description="本章关键事件列表")


class ParseResponse(BaseModel):
    """解析请求的响应"""
    chapter_id: int = Field(..., description="已解析的章节号")
    parse_result: ChapterParseResult = Field(..., description="解析结果")
    from_cache: bool = Field(default=False, description="是否来自缓存")


class CharacterListResponse(BaseModel):
    """人物列表 API 响应"""
    novel_name: str = Field(..., description="小说名称")
    characters: list[Character] = Field(default_factory=list, description="已解锁的人物（去重）")


class RelationshipEdge(BaseModel):
    """关系网单条边"""
    source: str = Field(..., description="人物A")
    target: str = Field(..., description="人物B")
    relation: str = Field(..., description="关系描述")


class RelationshipGraph(BaseModel):
    """关系网 API 响应"""
    novel_name: str = Field(..., description="小说名称")
    nodes: list[str] = Field(default_factory=list, description="所有人物节点")
    edges: list[RelationshipEdge] = Field(default_factory=list, description="关系边")


class ImportNovelResponse(BaseModel):
    """导入小说成功后的响应"""
    novel_name: str = Field(..., description="小说名称")
    world_dir: str = Field(..., description="创建的世界浓缩文件夹路径")
    metadata_path: str = Field(..., description="元数据文件路径")
    timeline_path: str = Field(..., description="时间轴文件路径")
    assets_dir: str = Field(..., description="静态资源文件夹路径")
    chapters_path: str = Field(default="", description="章节索引文件路径")
    message: str = Field(..., description="导入结果消息")
