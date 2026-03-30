"""
Playwright 网页截图工具 — 截取指定 URL 的可视区域作为文章插图

用法：
    from agent.tools.screenshot import take_screenshot
    path = take_screenshot("https://example.com", description="Example homepage")
    # → "data/images/screenshot_1711800000.png"

依赖：
    uv pip install playwright
    python -m playwright install chromium
"""

import os
import time
from dataclasses import dataclass


@dataclass
class ScreenshotResult:
    """截图结果"""
    url: str        # 本地文件路径
    alt: str        # 描述文字
    credit: str     # 来源说明


def take_screenshot(
    target_url: str,
    description: str = "",
    width: int = 1280,
    height: int = 800,
    clip: dict | None = None,
) -> ScreenshotResult | None:
    """
    使用 Playwright 截取网页可视区域。

    Args:
        target_url:  要截图的 URL
        description: 图片描述（用于 alt 文字）
        width:       视口宽度，默认 1280
        height:      视口高度，默认 800
        clip:        可选裁剪区域 {"x": 0, "y": 0, "width": 1280, "height": 750}

    Returns:
        ScreenshotResult 或 None（失败时）
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [Screenshot] playwright 未安装，请运行: uv pip install playwright && python -m playwright install chromium")
        return None

    os.makedirs("data/images", exist_ok=True)
    basename = f"screenshot_{int(time.time())}_{hash(target_url) % 10000:04d}.png"
    filename = f"data/images/{basename}"

    print(f"  [Screenshot] 截图: {target_url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": width, "height": height})

            # 先尝试 networkidle（等待网络空闲），失败回退到 load + 延迟
            try:
                page.goto(target_url, wait_until="networkidle", timeout=30000)
            except Exception:
                page.goto(target_url, wait_until="load", timeout=30000)
                page.wait_for_timeout(2000)

            # 截图
            screenshot_opts: dict = {"path": filename}
            if clip:
                screenshot_opts["clip"] = clip
            else:
                screenshot_opts["full_page"] = False

            page.screenshot(**screenshot_opts)
            browser.close()

        print(f"  [Screenshot] 保存: {filename}")
        alt = description or target_url
        # 返回 API 可访问的 URL，与 upload-image 端点保持一致
        api_url = f"http://localhost:8917/api/images/{basename}"
        return ScreenshotResult(
            url=api_url,
            alt=alt,
            credit=description or target_url,
        )

    except Exception as e:
        print(f"  [Screenshot] 截图失败 ({target_url}): {e}")
        return None
