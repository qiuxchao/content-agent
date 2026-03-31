"""
统一配置读取 — 优先级：环境变量 > SQLite settings 表 > default

用法：
    from agent.config import get_config
    api_key = get_config("LLM_API_KEY")
"""

import os
from agent.db import get_setting


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8917").rstrip("/")


def get_config(key: str, default: str = "") -> str:
    """
    读取配置值。优先级：环境变量 > SQLite settings 表 > default。
    环境变量中的空字符串视为未配置，继续回退到 SQLite。
    """
    env_val = os.getenv(key, "").strip()
    if env_val:
        return env_val
    db_val = get_setting(key)
    if db_val:
        return db_val
    return default
