"""
微信公众号 API 客户端

功能：
  1. 获取 access_token
  2. 上传封面图到素材库
  3. 创建草稿（发布到草稿箱）

API 文档：https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html
"""

import os
import tempfile
import requests
from agent.config import get_config

_BASE_URL = "https://api.weixin.qq.com/cgi-bin"


def _find_cjk_font() -> str | None:
    """查找系统中可用的中文字体路径"""
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",        # macOS
        "/System/Library/Fonts/Hiragino Sans GB.ttc",      # macOS
        "/System/Library/Fonts/Supplemental/Songti.ttc",   # macOS
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",                    # Windows 微软雅黑
        "C:\\Windows\\Fonts\\simhei.ttf",                  # Windows 黑体
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _create_placeholder_cover(title: str = "", summary: str = "") -> str:
    """
    生成一张 900x383 的封面图（约 2.35:1），返回临时文件路径。

    设计：
    - 暖色渐变背景
    - 标题文字居中
    - 底部装饰线条
    """
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 383
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # ── 暖色渐变背景 ──
    top_color = (26, 26, 46)       # 深蓝灰 #1A1A2E
    bottom_color = (44, 62, 80)    # 深蓝 #2C3E50
    for y in range(H):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * y / H)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * y / H)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── 装饰：顶部和底部的金色细线 ──
    accent = (255, 214, 0)  # 金色 #FFD600
    draw.line([(60, 40), (W - 60, 40)], fill=accent, width=2)
    draw.line([(60, H - 40), (W - 60, H - 40)], fill=accent, width=2)

    # ── 装饰：角落点缀 ──
    dot_r = 3
    for x, y in [(70, 40), (W - 70, 40), (70, H - 40), (W - 70, H - 40)]:
        draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=accent)

    # ── 标题文字 ──
    if title:
        title = title.lstrip("# ").strip().replace("**", "")

        font_path = _find_cjk_font()
        if font_path:
            # 根据标题长度自适应字号
            font_size = 38 if len(title) <= 20 else 32 if len(title) <= 30 else 26
            font = ImageFont.truetype(font_path, font_size)

            # 自动换行
            max_width = W - 160
            lines: list[str] = []
            current = ""
            for ch in title:
                test = current + ch
                bbox = font.getbbox(test)
                if bbox[2] - bbox[0] > max_width:
                    lines.append(current)
                    current = ch
                else:
                    current = test
            if current:
                lines.append(current)
            lines = lines[:3]  # 最多 3 行

            line_height = font_size + 10
            total_h = line_height * len(lines)
            y_start = (H - total_h) // 2 - 5

            for i, line in enumerate(lines):
                bbox = font.getbbox(line)
                tw = bbox[2] - bbox[0]
                x = (W - tw) // 2
                y = y_start + i * line_height
                draw.text((x, y), line, fill=(255, 255, 255), font=font)

            # 摘要（标题下方小字）
            if summary and len(lines) <= 2:
                summary_text = summary.lstrip("> ").strip()
                if len(summary_text) > 40:
                    summary_text = summary_text[:38] + "..."
                small_font = ImageFont.truetype(font_path, 16)
                bbox = small_font.getbbox(summary_text)
                sw = bbox[2] - bbox[0]
                sy = y_start + total_h + 15
                draw.text(((W - sw) // 2, sy), summary_text, fill=(180, 180, 200), font=small_font)
        else:
            # 没有中文字体，用默认字体只写英文部分
            draw.text((W // 2 - 40, H // 2 - 10), "ARTICLE", fill=(255, 255, 255))

    path = os.path.join(tempfile.gettempdir(), "wechat_cover.png")
    img.save(path, "PNG")
    return path


def _get_credentials() -> tuple[str, str]:
    """获取微信 API 凭证（env > SQLite > 报错）"""
    app_id = get_config("WECHAT_APP_ID")
    app_secret = get_config("WECHAT_APP_SECRET")
    if not app_id or not app_secret:
        raise ValueError(
            "未配置微信公众号 API 凭证。\n"
            "请在设置中填写 WECHAT_APP_ID 和 WECHAT_APP_SECRET。\n"
            "获取方式：mp.weixin.qq.com → 开发 → 基本配置"
        )
    return app_id, app_secret


def get_access_token() -> str:
    """获取微信 API access_token（有效期 2 小时）"""
    app_id, app_secret = _get_credentials()
    resp = requests.get(
        f"{_BASE_URL}/token",
        params={
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        },
        timeout=10,
    )
    data = resp.json()
    if "access_token" not in data:
        raise RuntimeError(f"获取 access_token 失败：{data.get('errmsg', data)}")
    return data["access_token"]


def upload_image(access_token: str, image_path: str) -> str:
    """
    上传图片到微信素材库，返回 media_id。
    用于封面图（material/add_material 接口）。
    """
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"{_BASE_URL}/material/add_material",
            params={"access_token": access_token, "type": "image"},
            files={"media": (os.path.basename(image_path), f, "image/png")},
            timeout=30,
        )
    data = resp.json()
    if "media_id" not in data:
        raise RuntimeError(f"上传图片失败：{data.get('errmsg', data)}")
    return data["media_id"]


def _ensure_compatible_format(image_path: str) -> tuple[str, bool]:
    """
    微信只支持 jpg/png，遇到 webp 等格式先转成 png。
    返回 (可用的图片路径, 是否为临时文件需要清理)。
    """
    if not image_path.lower().endswith(".webp"):
        return image_path, False
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGBA")
        converted = image_path.rsplit(".", 1)[0] + ".png"
        if os.path.dirname(image_path) == "":
            converted = os.path.join(tempfile.gettempdir(), os.path.basename(converted))
        img.save(converted, "PNG")
        return converted, True
    except ImportError:
        raise RuntimeError("需要 Pillow 来转换 webp 图片，请运行: pip install Pillow")


def upload_body_image(access_token: str, image_path: str) -> str:
    """
    上传正文图片到微信，返回微信 URL。
    用于文章内的图片（media/uploadimg 接口，只返回 URL 不返回 media_id）。
    微信不支持 webp，会自动转为 png。
    """
    actual_path, need_cleanup = _ensure_compatible_format(image_path)
    try:
        with open(actual_path, "rb") as f:
            resp = requests.post(
                f"{_BASE_URL}/media/uploadimg",
                params={"access_token": access_token},
                files={"media": (os.path.basename(actual_path), f, "image/png")},
                timeout=30,
            )
    finally:
        if need_cleanup and os.path.exists(actual_path):
            os.unlink(actual_path)
    data = resp.json()
    if "url" not in data:
        raise RuntimeError(f"上传正文图片失败：{data.get('errmsg', data)}")
    # 确保 https
    url = data["url"]
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def _resolve_local_path(image_url: str) -> str | None:
    """
    如果是本地 API 提供的图片 URL（localhost），直接返回磁盘路径，避免 HTTP 回环下载。
    """
    import re as _re
    match = _re.search(r"https?://localhost[:\d]*/api/images/(.+)$", image_url)
    if not match:
        return None
    filename = match.group(1)
    # data/images/ 相对于项目根目录
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "images", filename)
    if os.path.exists(local_path):
        return local_path
    return None


def upload_body_image_from_url(access_token: str, image_url: str) -> str:
    """
    下载外部图片并上传到微信，返回微信 URL。
    对 localhost 图片直接读磁盘，避免回环超时。
    """
    # 优先检查是否为本地图片
    local_path = _resolve_local_path(image_url)
    if local_path:
        print(f"  [WeChat] 本地图片，直接读取: {os.path.basename(local_path)}")
        return upload_body_image(access_token, local_path)

    # 外部图片：下载后再上传
    resp = requests.get(image_url, timeout=15, proxies={"http": None, "https": None})
    if resp.status_code != 200:
        raise RuntimeError(f"下载图片失败: {image_url}")

    suffix = ".jpg"
    content_type = resp.headers.get("content-type", "")
    if "png" in content_type:
        suffix = ".png"
    elif "webp" in content_type:
        suffix = ".webp"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(resp.content)
        path = tmp.name

    try:
        return upload_body_image(access_token, path)
    finally:
        os.unlink(path)


def create_draft(
    access_token: str,
    title: str,
    content_html: str,
    summary: str = "",
    author: str = "",
    thumb_media_id: str = "",
) -> str:
    """
    创建草稿（发布到草稿箱），返回 media_id。
    用户可在 mp.weixin.qq.com 的「内容管理 → 草稿箱」中查看和发布。
    """
    if not author:
        author = get_config("WECHAT_DEFAULT_AUTHOR")

    # 清理标题中可能残留的 Markdown 格式
    title = title.lstrip("# ").strip().replace("**", "").replace("*", "")

    # 微信字段长度限制：标题 64 字符，摘要 120 字符，作者 8 字符
    if len(title) > 64:
        title = title[:61] + "..."
    # 微信 digest 字段限制很严格（约 54 字节），超出直接留空让微信自动截取
    if summary and len(summary.encode("utf-8")) > 54:
        # 按字节截断
        result_s = ""
        for char in summary:
            if len((result_s + char).encode("utf-8")) > 51:
                summary = result_s + "..."
                break
            result_s += char
        if len(summary.encode("utf-8")) > 54:
            summary = ""  # 还是超了就不传
    if author and len(author) > 8:
        author = author[:8]

    print(f"  [WeChat] 标题: '{title}' | 摘要: '{summary[:20]}...' | 作者: '{author}' | 内容: {len(content_html)}字符")

    article = {
        "title": title,
        "author": author,
        "content": content_html,
        "digest": summary,
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }

    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id

    import json
    resp = requests.post(
        f"{_BASE_URL}/draft/add",
        params={"access_token": access_token},
        data=json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=30,
    )
    data = resp.json()
    if "media_id" not in data:
        raise RuntimeError(f"创建草稿失败：{data.get('errmsg', data)}")
    return data["media_id"]


def check_configured() -> bool:
    """检查微信 API 是否已配置（env > SQLite）"""
    return bool(get_config("WECHAT_APP_ID") and get_config("WECHAT_APP_SECRET"))


def publish_article(
    md_text: str,
    theme: str = "default",
    title: str = "",
    summary: str = "",
    author: str = "",
    cover_path: str = "",
) -> dict:
    """
    一站式发布：Markdown → HTML → 上传封面 → 创建草稿

    返回 { "media_id": str, "title": str, "summary": str }
    """
    from agent.publish.wechat_html import md_to_wechat_html

    # 1. 转换 HTML
    result = md_to_wechat_html(md_text, theme=theme)
    html = result["html"]
    if not title:
        title = result["title"]
    if not summary:
        summary = result["summary"]

    # 2. 获取 token
    token = get_access_token()

    # 3. 上传正文中的外部图片到微信素材库，替换 URL
    import re as _re
    img_pattern = _re.compile(r'<img([^>]*?)src="(https?://[^"]+)"([^>]*?)/?\s*>')
    matches = img_pattern.findall(html)
    for before_src, img_url, after_src in matches:
        try:
            print(f"  [WeChat] 上传正文图片: {img_url[:60]}...")
            wechat_url = upload_body_image_from_url(token, img_url)
            old_tag = f'<img{before_src}src="{img_url}"{after_src}>'
            # 如果原标签不是自闭合的也匹配
            new_tag = f'<img src="{wechat_url}" style="display:block;width:100%;margin:1.5em auto;">'
            html = html.replace(old_tag, new_tag, 1)
        except Exception as e:
            print(f"  [WeChat] 图片上传失败，跳过: {e}")
            # 上传失败就去掉这张图，不影响发布
            html = html.replace(f'<img{before_src}src="{img_url}"{after_src}>', '', 1)

    # 4. 上传封面（必须有，微信 API 要求）
    if cover_path and os.path.exists(cover_path):
        thumb_media_id = upload_image(token, cover_path)
    else:
        placeholder = _create_placeholder_cover(title=title, summary=summary)
        thumb_media_id = upload_image(token, placeholder)
        os.unlink(placeholder)

    # 5. 创建草稿
    media_id = create_draft(
        access_token=token,
        title=title,
        content_html=html,
        summary=summary,
        author=author,
        thumb_media_id=thumb_media_id,
    )

    return {
        "media_id": media_id,
        "title": title,
        "summary": summary,
    }
