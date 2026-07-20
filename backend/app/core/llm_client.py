"""
LLM 客户端 - 封装 Instructor + OpenAI/DeepSeek 调用。

特性：
- 异步调用（httpx）
- 自动重试（3 次）
- Instructor 强类型输出
- 支持 OpenAI / DeepSeek 等 OpenAI-compatible 接口

配置通过环境变量注入（参见 core/config.py）：
- LLM_API_KEY
- LLM_BASE_URL（默认 DeepSeek）
- LLM_MODEL（默认 deepseek-chat）
"""

from __future__ import annotations

import asyncio
import logging
from typing import Type, TypeVar

import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def _create_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )


async def structured_completion(
    prompt: str,
    response_model: Type[T],
    system_message: str = "你是一个专业的小说分析助手。",
    max_retries: int | None = None,
) -> T:
    """
    发送 prompt 到大模型，返回强类型结构化结果。

    Args:
        prompt: 用户 prompt 内容。
        response_model: Pydantic 模型（Instructor 用它做 schema 约束）。
        system_message: 系统角色设定。
        max_retries: 最大重试次数，默认使用全局配置。

    Returns:
        强类型的 Pydantic 模型实例。

    Raises:
        ValueError: API Key 未配置。
        Exception: 重试耗尽后仍失败。
    """
    if not settings.llm_api_key:
        raise ValueError(
            "LLM_API_KEY 环境变量未设置。\n"
            "请设置：set LLM_API_KEY=sk-xxx  (Windows)  "
            "或 export LLM_API_KEY=sk-xxx  (Mac/Linux)"
        )

    retries = max_retries if max_retries is not None else settings.llm_max_retries
    client = await _create_client()
    aclient = instructor.from_openai(client)

    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            result = await aclient.chat.completions.create(
                model=settings.llm_model,
                response_model=response_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
            )
            return result  # type: ignore[return-value]

        except Exception as e:
            last_error = e
            logger.warning(
                "LLM 调用失败 (第 %d/%d 次)：%s", attempt, retries, e
            )
            if attempt < retries:
                await asyncio.sleep(2 ** attempt)

    raise last_error  # type: ignore[misc]
