"""
全局配置 — 通过环境变量注入，优先读取项目根目录的 .env 文件。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


class Settings:
    @property
    def llm_api_key(self) -> str:
        return os.environ.get("LLM_API_KEY", "")

    @property
    def llm_base_url(self) -> str:
        return os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")

    @property
    def llm_model(self) -> str:
        return os.environ.get("LLM_MODEL", "deepseek-chat")

    @property
    def llm_max_retries(self) -> int:
        return int(os.environ.get("LLM_MAX_RETRIES", "3"))


settings = Settings()
