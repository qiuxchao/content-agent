"""
AI 图片生成工具 — 统一多 Provider 接口

支持的 Provider：
  - openai    : OpenAI 兼容 /images/generations（含 gpt-image、DALL-E、Seedream/豆包 等）
  - gemini    : Google Gemini（原生 generateContent API）
  - openrouter: OpenRouter 聚合（通过 /chat/completions，可用 Gemini、FLUX 等）
  - replicate : Replicate 托管模型，如 Google nano-banana-pro（按量付费）
  - dashscope : 通义万相 qwen-image-2.0

配置方式（统一使用 IMAGE_* 前缀）：
  IMAGE_PROVIDER=openai          # 默认 provider
  IMAGE_API_KEY=sk-...           # API 密钥（留空复用 LLM_API_KEY）
  IMAGE_BASE_URL=                # 自定义 API 地址（留空使用 provider 默认）
  IMAGE_MODEL=gpt-image-1        # 可选，不填则用 provider 默认值
  IMAGE_STYLE=warm               # 风格预设，见 STYLE_PRESETS
"""

import os
import base64
import time
import requests
from dataclasses import dataclass
from agent.config import get_config


@dataclass
class GeneratedImage:
    """生成的图片"""
    url: str        # 图片 URL（可直接展示）
    alt: str        # 描述文字
    credit: str     # 署名 / 来源说明


# ── 风格预设（参考 baoyu-skills 风格体系）──────────────────────
STYLE_PRESETS: dict[str, dict] = {
    "warm": {
        "label": "温暖",
        "prompt": (
            "Warm, cozy hand-drawn illustration style. "
            "Soft color palette: cream, warm orange, dusty rose, sage green. "
            "Gentle watercolor textures, rounded shapes, friendly feel. "
            "Simple decorative elements like small leaves, stars, coffee cups."
        ),
    },
    "fresh": {
        "label": "新鲜",
        "prompt": (
            "Fresh, clean illustration style. "
            "Color palette: mint green, sky blue, light coral, white. "
            "Crisp lines, modern flat design with subtle shadows. "
            "Nature-inspired decorations: leaves, flowers, droplets."
        ),
    },
    "minimal": {
        "label": "极简",
        "prompt": (
            "Minimalist illustration style with lots of whitespace. "
            "Monochrome with one accent color. "
            "Simple line art, geometric shapes, elegant typography. "
            "Clean, sophisticated, zen-like composition."
        ),
    },
    "notion": {
        "label": "概念",
        "prompt": (
            "Notion-style clean illustration. "
            "Black and white base with pastel blue accents (#A8D4F0). "
            "Simple line doodles, geometric shapes, stick figures. "
            "Organized grid layout, clean hand-drawn lettering."
        ),
    },
    "retro": {
        "label": "复古",
        "prompt": (
            "Retro vintage illustration style. "
            "Muted color palette: rust, olive, mustard, faded teal. "
            "Halftone dot textures, aged paper feel, stamp-like elements. "
            "Nostalgic, 70s-80s aesthetic with rounded typography."
        ),
    },
    "bold": {
        "label": "粗体",
        "prompt": (
            "Bold, high-contrast graphic style. "
            "Strong primary colors: red, yellow, black, white. "
            "Thick outlines, block shapes, impactful visual hierarchy. "
            "Street art influence, energetic and attention-grabbing."
        ),
    },
    "cute": {
        "label": "可爱",
        "prompt": (
            "Cute kawaii illustration style. "
            "Pastel pink, lavender, baby blue, peach color palette. "
            "Round adorable characters, sparkles, hearts, cloud shapes. "
            "Soft gradients, playful hand-drawn elements."
        ),
    },
    "chalkboard": {
        "label": "黑板",
        "prompt": (
            "Chalkboard illustration style on dark background. "
            "White and colored chalk on dark green/black surface. "
            "Hand-drawn chalk lettering, sketchy diagrams, doodles. "
            "Educational feel with chalk dust texture effects."
        ),
    },
}

DEFAULT_STYLE = "warm"

# 平台推荐风格
PLATFORM_STYLES: dict[str, str] = {
    "wechat": "warm",
    "xiaohongshu": "fresh",
    "zhihu": "minimal",
}


def _get_style_prompt(style: str | None, platform: str | None) -> str:
    """获取风格 prompt 片段"""
    if not style:
        style = PLATFORM_STYLES.get(platform or "", DEFAULT_STYLE)
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS[DEFAULT_STYLE])
    return preset["prompt"]


def build_image_prompt(keyword: str, style: str | None = None, platform: str | None = None) -> str:
    """构建完整的图片生成 prompt"""
    style_prompt = _get_style_prompt(style, platform)
    return (
        f"Create an illustration about: {keyword}. "
        f"Style: {style_prompt} "
        f"The image should be visually appealing, suitable for a blog article. "
        f"No text or words in the image. Landscape orientation 16:9."
    )


# ── Provider 实现 ────────────────────────────────────────────

def _get_image_config() -> tuple[str, str, str]:
    """获取统一的生图配置：(api_key, base_url, model)"""
    api_key = get_config("IMAGE_API_KEY") or get_config("LLM_API_KEY")
    base_url = get_config("IMAGE_BASE_URL")
    model = get_config("IMAGE_MODEL")
    return api_key, base_url, model


def _generate_openai(prompt: str, model: str | None = None) -> str | None:
    """OpenAI 兼容 /images/generations（含 gpt-image、DALL-E、Seedream/豆包 等）"""
    cfg_key, cfg_url, cfg_model = _get_image_config()
    api_key = cfg_key
    base_url = cfg_url or "https://api.openai.com/v1"
    model = model or cfg_model or "gpt-image-1"

    if not api_key:
        print("  [ImageGen] 未配置 IMAGE_API_KEY")
        return None

    # 构建请求参数
    body: dict = {"model": model, "prompt": prompt, "n": 1}

    # gpt-image 系列用 1536x1024，dall-e-3 用 1792x1024，其他不传 size 让服务端决定
    if model.startswith("gpt-image"):
        body["size"] = "1536x1024"
        body["quality"] = "medium"
    elif model.startswith("dall-e-3"):
        body["size"] = "1792x1024"
        body["quality"] = "standard"
    elif "seedream" in model:
        body["size"] = "2K"
        body["response_format"] = "url"
        body["watermark"] = False

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=90,
        )
        if resp.status_code != 200:
            print(f"  [ImageGen/OpenAI] 请求失败 ({resp.status_code}): {resp.text[:200]}")
            return None
        data = resp.json()["data"][0]
        return data.get("url") or _save_b64(data.get("b64_json"), "openai")
    except Exception as e:
        print(f"  [ImageGen/OpenAI] 异常: {e}")
        return None


def _generate_gemini(prompt: str, model: str | None = None) -> str | None:
    """Google Gemini 生图（原生 generateContent API）"""
    cfg_key, cfg_url, cfg_model = _get_image_config()
    api_key = cfg_key
    base_url = cfg_url or "https://generativelanguage.googleapis.com"
    model = model or cfg_model or "gemini-2.0-flash-preview-image-generation"

    if not api_key:
        print("  [ImageGen] 未配置 IMAGE_API_KEY (Gemini)")
        return None

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                },
            },
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"  [ImageGen/Gemini] 请求失败 ({resp.status_code}): {resp.text[:200]}")
            return None

        candidates = resp.json().get("candidates", [])
        if not candidates:
            print("  [ImageGen/Gemini] 返回为空")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData", {})
            if inline.get("data"):
                return _save_b64(inline["data"], "gemini")

        print("  [ImageGen/Gemini] 未找到图片内容")
        return None
    except Exception as e:
        print(f"  [ImageGen/Gemini] 异常: {e}")
        return None


def _generate_openrouter(prompt: str, model: str | None = None) -> str | None:
    """OpenRouter 生图（聚合多模型，通过 /chat/completions）"""
    cfg_key, cfg_url, cfg_model = _get_image_config()
    api_key = cfg_key
    base_url = cfg_url or "https://openrouter.ai/api/v1"
    model = model or cfg_model or "google/gemini-2.0-flash-preview-image-generation"

    if not api_key:
        print("  [ImageGen] 未配置 IMAGE_API_KEY (OpenRouter)")
        return None

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                "modalities": ["image", "text"],
                "max_tokens": 256,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"  [ImageGen/OpenRouter] 请求失败 ({resp.status_code}): {resp.text[:200]}")
            return None

        choices = resp.json().get("choices", [])
        if not choices:
            print("  [ImageGen/OpenRouter] 返回为空")
            return None

        msg = choices[0].get("message", {})

        # 格式1: message.images[].image_url
        images = msg.get("images", [])
        if images:
            img_url = images[0].get("image_url", "")
            if img_url.startswith("data:image"):
                b64 = img_url.split(",", 1)[1] if "," in img_url else img_url
                return _save_b64(b64, "openrouter")
            if img_url.startswith("http"):
                return img_url

        # 格式2: message.content 数组中提取 image_url
        content = msg.get("content", [])
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:image"):
                        b64 = url.split(",", 1)[1] if "," in url else url
                        return _save_b64(b64, "openrouter")
                    if url.startswith("http"):
                        return url

        print("  [ImageGen/OpenRouter] 未找到图片内容")
        return None
    except Exception as e:
        print(f"  [ImageGen/OpenRouter] 异常: {e}")
        return None


def _generate_replicate(prompt: str, model: str | None = None) -> str | None:
    """Replicate 生图（nano-banana-pro 等）"""
    cfg_key, cfg_url, cfg_model = _get_image_config()
    api_key = cfg_key or get_config("REPLICATE_API_TOKEN")
    base_url = cfg_url or "https://api.replicate.com"
    model = model or cfg_model or "google/nano-banana-pro"

    if not api_key:
        print("  [ImageGen] 未配置 IMAGE_API_KEY / REPLICATE_API_TOKEN")
        return None

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/v1/models/{model}/predictions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Prefer": "wait=60",
            },
            json={"input": {"prompt": prompt, "aspect_ratio": "16:9"}},
            timeout=90,
        )
        if resp.status_code not in (200, 201):
            print(f"  [ImageGen/Replicate] 创建失败 ({resp.status_code}): {resp.text[:200]}")
            return None

        result = resp.json()

        if result.get("status") == "succeeded":
            output = result.get("output")
            return output[0] if isinstance(output, list) else output

        poll_url = result.get("urls", {}).get("get") or f"{base_url}/v1/predictions/{result['id']}"
        for _ in range(60):
            time.sleep(2)
            poll = requests.get(poll_url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
            r = poll.json()
            if r.get("status") == "succeeded":
                output = r.get("output")
                return output[0] if isinstance(output, list) else output
            if r.get("status") in ("failed", "canceled"):
                print(f"  [ImageGen/Replicate] 失败: {r.get('error', 'unknown')}")
                return None

        print("  [ImageGen/Replicate] 超时")
        return None
    except Exception as e:
        print(f"  [ImageGen/Replicate] 异常: {e}")
        return None


def _generate_dashscope(prompt: str, model: str | None = None) -> str | None:
    """通义万相 qwen-image 生图"""
    cfg_key, cfg_url, cfg_model = _get_image_config()
    api_key = cfg_key or get_config("DASHSCOPE_API_KEY")
    base_url = cfg_url or "https://dashscope.aliyuncs.com"
    model = model or cfg_model or "qwen-image-2.0-pro"

    if not api_key:
        print("  [ImageGen] 未配置 IMAGE_API_KEY / DASHSCOPE_API_KEY")
        return None

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/api/v1/services/aigc/multimodal-generation/generation",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "input": {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                },
                "parameters": {
                    "size": "1024*576",
                    "prompt_extend": False,
                    "watermark": False,
                },
            },
            timeout=90,
        )
        if resp.status_code != 200:
            print(f"  [ImageGen/DashScope] 请求失败 ({resp.status_code}): {resp.text[:200]}")
            return None

        output = resp.json().get("output", {})

        choices = output.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", [])
            for item in content:
                if "image" in item:
                    return item["image"]

        result_image = output.get("result_image")
        if result_image:
            if result_image.startswith("http"):
                return result_image
            return _save_b64(result_image, "dashscope")

        print(f"  [ImageGen/DashScope] 未知返回格式: {list(output.keys())}")
        return None
    except Exception as e:
        print(f"  [ImageGen/DashScope] 异常: {e}")
        return None


def _save_b64(b64_data: str | None, prefix: str) -> str | None:
    """将 base64 图片保存到 data/ 目录，返回本地路径"""
    if not b64_data:
        return None
    os.makedirs("data/images", exist_ok=True)
    filename = f"data/images/{prefix}_{int(time.time())}.png"
    with open(filename, "wb") as f:
        f.write(base64.b64decode(b64_data))
    return filename


# ── 统一入口 ────────────────────────────────────────────────

_PROVIDERS: dict[str, callable] = {
    "openai": _generate_openai,
    "gemini": _generate_gemini,
    "openrouter": _generate_openrouter,
    "replicate": _generate_replicate,
    "dashscope": _generate_dashscope,
}


def _detect_provider() -> str | None:
    """根据已配置的 IMAGE_API_KEY 自动检测可用的 provider"""
    if get_config("IMAGE_API_KEY"):
        return "openai"
    if get_config("REPLICATE_API_TOKEN"):
        return "replicate"
    if get_config("DASHSCOPE_API_KEY"):
        return "dashscope"
    base_url = get_config("LLM_BASE_URL")
    if "dashscope" in base_url:
        return "dashscope"
    if get_config("LLM_API_KEY"):
        return "openai"
    return None


def generate_image(
    keyword: str,
    style: str | None = None,
    platform: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> GeneratedImage | None:
    """
    AI 生成一张图片。

    Args:
        keyword:  图片内容关键词（英文）
        style:    风格预设 key（warm/fresh/minimal 等），不传则按平台默认
        platform: 目标平台，用于选择默认风格
        provider: 指定 provider，不传则自动检测
        model:    指定模型，不传则用 provider 默认

    Returns:
        GeneratedImage 或 None（失败时）
    """
    provider = provider or get_config("IMAGE_PROVIDER") or _detect_provider()
    if not provider or provider not in _PROVIDERS:
        print(f"  [ImageGen] 不支持的 provider: {provider}")
        return None

    prompt = build_image_prompt(keyword, style, platform)
    print(f"  [ImageGen/{provider}] 生成图片: {keyword}")

    url = _PROVIDERS[provider](prompt, model)
    if not url:
        return None

    style_name = style or PLATFORM_STYLES.get(platform or "", DEFAULT_STYLE)
    return GeneratedImage(
        url=url,
        alt=keyword,
        credit=f"AI Generated ({style_name} style)",
    )
