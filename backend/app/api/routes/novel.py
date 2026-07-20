"""
小说导入与管理 API 路由。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.app.models.world_models import (
    ChapterContent,
    ChapterIndex,
    CharacterListResponse,
    ImportNovelResponse,
    ParseResponse,
    RelationshipGraph,
)
from backend.app.services.chapter_parser import (
    get_characters,
    get_relationships,
    parse_chapter,
)
from backend.app.services.chapter_splitter import (
    load_chapter_index,
)
from backend.app.services.novel_importer import (
    create_world_directory,
    delete_novel,
    get_chapter,
    get_chapters_index_path,
    list_imported_novels,
    load_timeline,
    load_world_metadata,
)

router = APIRouter(prefix="/api/novels", tags=["novels"])


@router.post("/import", response_model=ImportNovelResponse)
async def import_novel(file: UploadFile, novel_name: str | None = None) -> ImportNovelResponse:
    """
    导入一本 TXT 小说。

    上传 TXT 文件后，服务端会自动：
    1. 保存 TXT 到临时位置
    2. 创建世界浓缩文件夹目录结构
    3. 生成初始 world_metadata.json 和 timeline.json

    Args:
        file: 上传的 TXT 小说文件。
        novel_name: 可选的小说名称，不传则使用文件名（去掉后缀）。

    Returns:
        ImportNovelResponse: 包含所有创建路径的响应。
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    # 校验文件类型
    if not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="仅支持 .txt 格式的小说文件")

    # 确定小说名称
    name = novel_name or Path(file.filename).stem

    # 将上传文件保存到临时位置
    try:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 调用服务创建世界浓缩文件夹
        result = create_world_directory(tmp_path, name)

        return ImportNovelResponse(**result)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"文件写入失败：{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败：{e}")
    finally:
        # 清理临时文件
        tmp_path_local = tmp_path  # type: ignore[possibly-undefined]
        Path(tmp_path_local).unlink(missing_ok=True)


@router.get("/list", response_model=list[str])
async def list_novels() -> list[str]:
    """列出所有已导入的小说名称列表。"""
    return list_imported_novels()


@router.get("/{novel_name}/metadata")
async def get_novel_metadata(novel_name: str):
    """获取已导入小说的元数据。"""
    metadata = load_world_metadata(novel_name)
    if metadata is None:
        raise HTTPException(
            status_code=404,
            detail=f"小说「{novel_name}」尚未导入",
        )
    return metadata


@router.get("/{novel_name}/timeline")
async def get_novel_timeline(novel_name: str):
    """获取已导入小说的章节时间轴数据。"""
    timeline = load_timeline(novel_name)
    if timeline is None:
        raise HTTPException(
            status_code=404,
            detail=f"小说「{novel_name}」尚未导入",
        )
    return timeline


@router.get("/{novel_name}/chapters", response_model=ChapterIndex)
async def list_chapters(novel_name: str) -> ChapterIndex:
    """获取小说的章节索引（标题 + 行号范围）。"""
    chapters_path = get_chapters_index_path(novel_name)
    if not chapters_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"小说「{novel_name}」尚未导入或缺少 chapters.json",
        )
    return load_chapter_index(chapters_path)


@router.get("/{novel_name}/chapter/{chapter_id}", response_model=ChapterContent)
async def read_chapter(novel_name: str, chapter_id: int) -> ChapterContent:
    """获取指定章节的正文内容。"""
    try:
        return get_chapter(novel_name, chapter_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except IndexError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{novel_name}/parse/{chapter_id}", response_model=ParseResponse)
async def parse_chapter_endpoint(novel_name: str, chapter_id: int) -> ParseResponse:
    """触发 AI 解析指定章节，结果写入 timeline.json。"""
    timeline_path = get_chapters_index_path(novel_name).parent / "timeline.json"
    try:
        chapter = get_chapter(novel_name, chapter_id)
    except (FileNotFoundError, IndexError) as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        return await parse_chapter(
            novel_name=novel_name,
            chapter_id=chapter_id,
            chapter_title=chapter.chapter_title,
            chapter_content=chapter.content,
            timeline_path=timeline_path,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 解析失败：{e}")


@router.get("/{novel_name}/characters", response_model=CharacterListResponse)
async def list_characters(novel_name: str) -> CharacterListResponse:
    """获取当前已解锁的人物列表（从 timeline 聚合去重）。"""
    timeline_path = get_chapters_index_path(novel_name).parent / "timeline.json"
    return get_characters(novel_name, timeline_path)


@router.get("/{novel_name}/relationships", response_model=RelationshipGraph)
async def get_relationship_graph(novel_name: str) -> RelationshipGraph:
    """获取当前人物关系网数据。"""
    timeline_path = get_chapters_index_path(novel_name).parent / "timeline.json"
    return get_relationships(novel_name, timeline_path)


@router.delete("/{novel_name}")
async def remove_novel(novel_name: str) -> dict:
    """删除已导入的小说及其所有数据。"""
    if not delete_novel(novel_name):
        raise HTTPException(
            status_code=404,
            detail=f"小说「{novel_name}」不存在",
        )
    return {"message": f"小说「{novel_name}」已删除", "novel_name": novel_name}
