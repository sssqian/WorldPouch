"""
小说导入服务。

当用户导入一本 TXT 小说时，自动创建「世界浓缩文件夹」目录结构：

data/novels/{novel_name}_world/          # 根目录
├── world_metadata.json                  # 核心元数据
├── timeline.json                        # 章节时间轴数据
├── assets/                              # 静态资源文件夹
│   ├── characters/                      # 人物头像与插图
│   ├── maps/                            # 大地图及地标场景图
│   └── events/                          # 章节高潮事件插画
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from backend.app.models.world_models import (
    ChapterContent,
    TimelineData,
    WorldMetadata,
)
from backend.app.services.chapter_splitter import (
    get_chapter_content,
    load_chapter_index,
    save_chapter_index,
    split_chapters,
)

# 项目根目录下的 data/novels 文件夹
DATA_NOVELS_DIR = Path(__file__).resolve().parents[3] / "data" / "novels"


def _sanitize_novel_name(name: str) -> str:
    """清理小说名称，去除非法文件名字符，追加 _world 后缀。"""
    name = name.strip()
    # 替换 Windows 不允许的文件名字符
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return f"{name}_world"


def _ensure_directory(path: Path) -> Path:
    """确保目录存在，如不存在则创建。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _count_chapters(txt_path: Path) -> int:
    """粗略统计 TXT 文件的章节数（根据"第X章"或"第X回"等模式）。"""
    chapter_pattern = re.compile(r"第[\u4e00-\u9fff\d]+[章回节]")
    count = 0
    try:
        with open(txt_path, encoding="utf-8") as f:
            for line in f:
                if chapter_pattern.search(line):
                    count += 1
    except (UnicodeDecodeError, OSError):
        # 如果 UTF-8 失败，尝试 GBK 编码
        try:
            with open(txt_path, encoding="gbk") as f:
                for line in f:
                    if chapter_pattern.search(line):
                        count += 1
        except (UnicodeDecodeError, OSError):
            pass
    return max(count, 1)  # 至少 1 章


def create_world_directory(txt_path: str, novel_name: str) -> dict:
    """
    创建世界浓缩文件夹的完整目录结构。

    Args:
        txt_path: TXT 小说文件的路径。
        novel_name: 小说名称（如"斗破苍穹"）。

    Returns:
        包含各创建路径的字典。

    Raises:
        FileNotFoundError: TXT 文件不存在。
        OSError: 目录创建或文件写入失败。
    """
    txt_file = Path(txt_path)
    if not txt_file.exists():
        raise FileNotFoundError(f"TXT 文件不存在：{txt_path}")

    # 1. 创建根目录 data/novels/{novel_name}_world/
    world_dir_name = _sanitize_novel_name(novel_name)
    world_dir = _ensure_directory(DATA_NOVELS_DIR / world_dir_name)

    # 2. 保存原始 TXT 到世界文件夹
    original_txt = world_dir / f"{novel_name}.txt"
    shutil.copy2(txt_path, original_txt)

    # 3. 创建 assets 子目录
    assets_dir = _ensure_directory(world_dir / "assets")
    characters_dir = _ensure_directory(assets_dir / "characters")
    maps_dir = _ensure_directory(assets_dir / "maps")
    events_dir = _ensure_directory(assets_dir / "events")

    # 4. 章节切分并生成 chapters.json
    chapter_index = split_chapters(original_txt)
    chapter_index.novel_name = novel_name
    chapters_path = world_dir / "chapters.json"
    save_chapter_index(chapter_index, chapters_path)
    total_chapters = len(chapter_index.chapters)

    # 5. 生成 world_metadata.json
    metadata = WorldMetadata(
        novel_name=novel_name,
        current_chapter=0,
        total_chapters=total_chapters,
    )
    metadata_path = world_dir / "world_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    # 6. 生成初始 timeline.json
    timeline = TimelineData(novel_name=novel_name)
    timeline_path = world_dir / "timeline.json"
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    return {
        "novel_name": novel_name,
        "world_dir": str(world_dir),
        "metadata_path": str(metadata_path),
        "timeline_path": str(timeline_path),
        "assets_dir": str(assets_dir),
        "chapters_path": str(chapters_path),
        "characters_dir": str(characters_dir),
        "maps_dir": str(maps_dir),
        "events_dir": str(events_dir),
        "message": f"世界浓缩文件夹创建成功！共检测到 {total_chapters} 章。",
    }


def load_world_metadata(novel_name: str) -> WorldMetadata | None:
    """加载已有世界浓缩文件夹的元数据。"""
    world_dir_name = _sanitize_novel_name(novel_name)
    metadata_path = DATA_NOVELS_DIR / world_dir_name / "world_metadata.json"
    if not metadata_path.exists():
        return None
    with open(metadata_path, encoding="utf-8") as f:
        data = json.load(f)
    return WorldMetadata(**data)


def load_timeline(novel_name: str) -> TimelineData | None:
    """加载已有世界浓缩文件夹的时间轴数据。"""
    world_dir_name = _sanitize_novel_name(novel_name)
    timeline_path = DATA_NOVELS_DIR / world_dir_name / "timeline.json"
    if not timeline_path.exists():
        return None
    with open(timeline_path, encoding="utf-8") as f:
        data = json.load(f)
    return TimelineData(**data)


def list_imported_novels() -> list[str]:
    """列出已导入的小说（扫描 data/novels/ 下所有 _world 目录）。"""
    if not DATA_NOVELS_DIR.exists():
        return []
    novels: list[str] = []
    for item in DATA_NOVELS_DIR.iterdir():
        if item.is_dir() and item.name.endswith("_world"):
            # 去掉 _world 后缀，得到原始小说名
            novels.append(item.name[: -len("_world")])
    return sorted(novels)


def delete_novel(novel_name: str) -> bool:
    """
    删除已导入的小说及其世界浓缩文件夹。

    Args:
        novel_name: 小说名称。

    Returns:
        True 表示成功删除，False 表示不存在。
    """
    world_dir = get_world_dir(novel_name)
    if not world_dir.exists():
        return False
    shutil.rmtree(world_dir)
    return True


def get_world_dir(novel_name: str) -> Path:
    """获取世界浓缩文件夹根目录路径。"""
    return DATA_NOVELS_DIR / _sanitize_novel_name(novel_name)


def get_chapters_index_path(novel_name: str) -> Path:
    """获取 chapters.json 路径。"""
    return get_world_dir(novel_name) / "chapters.json"


def get_original_txt_path(novel_name: str) -> Path:
    """获取原始 TXT 文件路径（导入时保存的副本）。"""
    return get_world_dir(novel_name) / f"{novel_name}.txt"


def get_chapter(novel_name: str, chapter_id: int) -> ChapterContent:
    """
    便捷查询函数：根据小说名和章节号直接获取正文。

    内部自动完成：加载索引 → 检查章节范围 → 按行号读取正文。

    Args:
        novel_name: 小说名称。
        chapter_id: 章节号（从 1 开始）。

    Returns:
        ChapterContent: 包含标题、正文和全书总章数。

    Raises:
        FileNotFoundError: 小说未导入或缺少 chapters.json。
        IndexError: 章节号超出范围。
    """
    chapters_path = get_chapters_index_path(novel_name)
    if not chapters_path.exists():
        raise FileNotFoundError(f"小说「{novel_name}」的章节索引不存在，请先导入")

    chapter_index = load_chapter_index(chapters_path)
    total = len(chapter_index.chapters)

    if chapter_id < 1 or chapter_id > total:
        raise IndexError(f"章节 {chapter_id} 不存在，共 {total} 章")

    chapter_item = chapter_index.chapters[chapter_id - 1]
    txt_path = get_original_txt_path(novel_name)
    content = get_chapter_content(txt_path, chapter_item)

    return ChapterContent(
        novel_name=novel_name,
        chapter_id=chapter_id,
        chapter_title=chapter_item.title,
        content=content,
        total_chapters=total,
    )
