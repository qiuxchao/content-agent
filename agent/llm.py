"""
LLM 工厂模块
统一读取 .env 配置，返回对应的 LLM 实例。

支持两种规范：
  - openai    兼容 OpenAI Chat Completions API（Kimi、DeepSeek、通义等均支持）
  - anthropic 原生 Anthropic API（Claude 系列）

.env 配置示例：

  # 使用 OpenAI 官方
  LLM_PROVIDER=openai
  LLM_API_KEY=sk-xxxx
  LLM_BASE_URL=https://api.openai.com/v1   # 可省略，这是默认值
  LLM_MODEL=gpt-4o-mini

  # 使用 Anthropic 官方
  LLM_PROVIDER=anthropic
  LLM_API_KEY=sk-ant-xxxx
  LLM_MODEL=claude-3-5-haiku-20241022
"""

import os
from functools import lru_cache
from langchain_core.language_models import BaseChatModel


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


@lru_cache(maxsize=4)
def get_llm() -> BaseChatModel:
    """
    根据环境变量返回 LLM 实例。
    结果会被缓存（只创建一次）。
    """
    provider = _get_env("LLM_PROVIDER", "openai").lower()
    api_key  = _get_env("LLM_API_KEY")
    model    = _get_env("LLM_MODEL", "gpt-4o-mini")

    if not api_key:
        raise ValueError("未设置 LLM_API_KEY，请检查 .env 文件")

    if provider == "anthropic":
        return _make_anthropic(api_key, model)
    elif provider == "openai":
        return _make_openai(api_key, model)
    else:
        raise ValueError(
            f"不支持的 LLM_PROVIDER: '{provider}'，"
            "请设置为 'openai' 或 'anthropic'"
        )


def _make_openai(api_key: str, model: str) -> BaseChatModel:
    """
    创建兼容 OpenAI 规范的 LLM。
    Kimi、DeepSeek、通义、硅基流动等只需改 base_url 和 model 即可。
    """
    from langchain_openai import ChatOpenAI

    base_url = _get_env("LLM_BASE_URL")  # 不填则使用 OpenAI 默认地址

    kwargs = dict(
        api_key=api_key,
        model=model,
        max_retries=3,       # 遇到 429/500 自动重试，最多 3 次
        request_timeout=120,  # 单次请求超时 120 秒
    )
    if base_url:
        kwargs["base_url"] = base_url

    print(f"  [LLM] OpenAI 规范 | model={model} | base_url={base_url or '(default)'}")
    return ChatOpenAI(**kwargs)


def _make_anthropic(api_key: str, model: str) -> BaseChatModel:
    """
    创建原生 Anthropic LLM。
    需要额外安装：uv add langchain-anthropic
    """
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise ImportError(
            "使用 Anthropic 规范需要安装额外依赖：\n"
            "  uv add langchain-anthropic"
        )

    print(f"  [LLM] Anthropic 规范 | model={model}")
    return ChatAnthropic(
        api_key=api_key,
        model_name=model,
    )