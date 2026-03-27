import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from agent.state import AgentState
from agent.config import get_config
from agent.tools.unsplash import search_images
from agent.tools.image_gen import generate_image, build_image_prompt, STYLE_PRESETS, PLATFORM_STYLES

# 匹配 [IMAGE: 任意内容]
IMAGE_PATTERN = re.compile(r"\[IMAGE:\s*([^\]]+)\]")


def _get_image_provider() -> str:
    """
    获取图片来源：prompt（仅提示词）、unsplash 或 ai。
    优先读 IMAGE_PROVIDER 配置，未配置则判断是否有 AI 生图的 key 可用。
    """
    provider = get_config("IMAGE_PROVIDER").lower()
    if provider == "prompt":
        return "prompt"
    if provider == "unsplash":
        return "unsplash"
    if provider in ("openai", "gemini", "openrouter", "replicate", "dashscope"):
        return "ai"
    # 未显式配置：检查是否有 Unsplash key
    if get_config("UNSPLASH_ACCESS_KEY"):
        return "unsplash"
    # 否则尝试 AI
    return "ai"


def _make_prompt_placeholder(keyword: str, style: str | None = None, platform: str | None = None) -> str:
    """生成 AI 绘图提示词占位符"""
    prompt = build_image_prompt(keyword, style, platform)
    return f"\n![{prompt}](prompt-placeholder)\n"


def _make_search_placeholder(keyword: str) -> str:
    """生成搜索关键词占位符（用于 Unsplash 等搜图场景）"""
    return f"\n![{keyword}](prompt-placeholder)\n"


def _fetch_unsplash(placeholder: str, keyword: str, **_) -> tuple[str, str, str]:
    """Unsplash 搜图，失败时生成关键词占位符"""
    imgs = search_images(keyword, count=1)
    if imgs:
        img = imgs[0]
        replacement = f"\n![{img.alt}]({img.url})\n*{img.credit}*\n"
        return placeholder, replacement, f"🖼️ 插图：{keyword}"
    replacement = _make_search_placeholder(keyword)
    return placeholder, replacement, f"📋 配图占位（可手动上传）：{keyword}"


def _fetch_ai(placeholder: str, keyword: str, style: str | None = None, platform: str | None = None) -> tuple[str, str, str]:
    """AI 生图，失败时生成绘图提示词占位符"""
    img = generate_image(keyword, style=style, platform=platform)
    if img:
        replacement = f"\n![{img.alt}]({img.url})\n*{img.credit}*\n"
        return placeholder, replacement, f"🎨 AI 插图：{keyword}"
    replacement = _make_prompt_placeholder(keyword, style, platform)
    return placeholder, replacement, f"📋 配图占位（可手动上传）：{keyword}"


def _fetch_ai_with_unsplash_fallback(placeholder: str, keyword: str, style: str | None = None, platform: str | None = None) -> tuple[str, str, str]:
    """AI 生图，失败时回退到 Unsplash，都失败则生成绘图提示词占位符"""
    ph, replacement, log = _fetch_ai(placeholder, keyword, style, platform)
    if replacement and "prompt-placeholder" not in replacement:
        return ph, replacement, log
    # 回退 Unsplash
    print(f"  [Fallback] AI 失败，尝试 Unsplash: {keyword}")
    ph2, replacement2, log2 = _fetch_unsplash(placeholder, keyword)
    if replacement2 and "prompt-placeholder" not in replacement2:
        return ph2, replacement2, log2
    # 都失败 → 用 AI 绘图提示词（信息更丰富）
    replacement = _make_prompt_placeholder(keyword, style, platform)
    return placeholder, replacement, f"📋 配图占位（可手动上传）：{keyword}"


def image_fetcher_node(state: AgentState) -> dict:
    """
    解析初稿中所有 [IMAGE: 关键词] 占位符，
    根据配置使用 Unsplash 搜图或 AI 生图，并发执行。
    """
    print("\n[ImageFetcher] 开始获取插图...")

    matches = list(IMAGE_PATTERN.finditer(state["draft"]))

    if not matches:
        print("  未找到插图占位符，跳过")
        return {
            "images": {},
            "final_article": state["draft"],
            "log": state.get("log", []) + ["🎉 文章生成完成！"],
        }

    # 去重
    unique: dict[str, str] = {}
    for match in matches:
        placeholder = match.group(0)
        if placeholder not in unique:
            unique[placeholder] = match.group(1).strip()

    # 选择图片来源
    source = _get_image_provider()
    platform = state.get("platform")
    style = state.get("image_style") or get_config("IMAGE_STYLE") or PLATFORM_STYLES.get(platform or "", None)

    image_map: dict[str, str] = {}
    logs: list[str] = []

    if source == "prompt":
        # 仅生成提示词占位符，不调用任何 API
        print("  图片来源：仅提示词（用户手动生图后上传）")
        for ph, kw in unique.items():
            replacement = _make_prompt_placeholder(kw, style, platform)
            image_map[ph] = replacement
            logs.append(f"📋 配图提示词：{kw}")
            print(f"  📋 配图提示词：{kw}")
    else:
        if source == "unsplash":
            fetch_fn = _fetch_unsplash
            print("  图片来源：Unsplash")
        else:
            fetch_fn = _fetch_ai_with_unsplash_fallback
            provider = get_config("IMAGE_PROVIDER") or "auto"
            style_label = STYLE_PRESETS.get(style or "", {}).get("label", style or "auto")
            print(f"  图片来源：AI 生图 (provider={provider}, style={style_label})")

        # 并发控制：IMAGE_CONCURRENT=true 时启用并发，默认串行（多数生图模型不支持并发）
        concurrent = get_config("IMAGE_CONCURRENT").lower() in ("true", "1", "yes")

        if concurrent:
            max_workers = 3 if source == "ai" else min(len(unique), 5)
            print(f"  并发模式：max_workers={max_workers}")
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(fetch_fn, ph, kw, style=style, platform=platform): ph
                    for ph, kw in unique.items()
                }
                for future in as_completed(futures):
                    ph, replacement, log = future.result()
                    image_map[ph] = replacement
                    logs.append(log)
                    print(f"  {log}")
        else:
            for ph, kw in unique.items():
                _, replacement, log = fetch_fn(ph, kw, style=style, platform=platform)
                image_map[ph] = replacement
                logs.append(log)
                print(f"  {log}")

    # 替换占位符
    final_article = state["draft"]
    for placeholder, replacement in image_map.items():
        final_article = final_article.replace(placeholder, replacement)

    print(f"  完成，共处理 {len(image_map)} 张插图")

    return {
        "images": image_map,
        "final_article": final_article,
        "log": state.get("log", []) + logs + ["🎉 文章生成完成！"],
    }
