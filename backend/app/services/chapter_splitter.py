"""
章节切分服务。

将 TXT 小说按章节标题模式（第X章/第X回等）切分为有序列表，
并生成 chapters.json 索引供快速按章读取。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.app.models.world_models import ChapterIndex, ChapterItem

# 章节标题匹配模式：第X章 / 第X回 / 第X节 / 第X卷
# 支持中文数字（一、二、三…）和阿拉伯数字（1, 2, 3…）
CHAPTER_HEADER_PATTERN = re.compile(
    r"^\s*第[\u4e00-\u9fff\d零一二三四五六七八九十百千万]+[章回节卷].*$"
)


def _read_lines(txt_path: Path) -> list[str]:
    """读取 TXT 文件全部行，自动探测编码（UTF-8 → GBK）。"""
    for encoding in ("utf-8", "gbk", "utf-16"):
        try:
            with open(txt_path, encoding=encoding) as f:
                return f.readlines()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别文件编码：{txt_path}")


def split_chapters(txt_path: Path) -> ChapterIndex:
    """
    扫描 TXT 文件，按章节标题切分并生成索引。

    Args:
        txt_path: TXT 小说文件路径。

    Returns:
        ChapterIndex: 包含所有章节索引条目。
    """
    lines = _read_lines(txt_path)
    total_lines = len(lines)

    # 第一遍扫描：找到所有章节标题行
    chapter_boundaries: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if CHAPTER_HEADER_PATTERN.match(line):
            chapter_boundaries.append((i, line.strip()))

    if not chapter_boundaries:
        # 整个文件没有检测到章节标题，当作单章处理
        chapters = [
            ChapterItem(
                id=1,
                title=txt_path.stem,
                start_line=0,
                end_line=total_lines,
            )
        ]
    else:
        chapters = []
        for idx, (start_line, title) in enumerate(chapter_boundaries):
            chapter_id = idx + 1
            # 本章结束行 = 下一章的起始行（如无下一章则为文件末尾）
            if idx + 1 < len(chapter_boundaries):
                end_line = chapter_boundaries[idx + 1][0]
            else:
                end_line = total_lines

            chapters.append(
                ChapterItem(
                    id=chapter_id,
                    title=title,
                    start_line=start_line,
                    end_line=end_line,
                )
            )

    return ChapterIndex(
        novel_name=txt_path.stem,
        chapters=chapters,
    )


def get_chapter_content(txt_path: Path, chapter_item: ChapterItem) -> str:
    """
    根据章节索引条目读取对应正文。

    Args:
        txt_path: TXT 文件路径。
        chapter_item: 章节索引条目（含 start_line / end_line）。

    Returns:
        str: 该章节的完整正文，行间保留原始换行。
    """
    lines = _read_lines(txt_path)
    chunk = lines[chapter_item.start_line : chapter_item.end_line]
    return "".join(chunk)


def save_chapter_index(chapter_index: ChapterIndex, output_path: Path) -> None:
    """将章节索引写入 chapters.json。"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chapter_index.model_dump(mode="json"), f, ensure_ascii=False, indent=2)


def load_chapter_index(json_path: Path) -> ChapterIndex:
    """从 chapters.json 加载章节索引。"""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    return ChapterIndex(**data)
