"""
Markdown → 微信公众号 HTML 转换器

核心流程：
  1. markdown 库解析 MD → HTML
  2. Pygments 处理代码高亮（直接生成内联样式）
  3. 加载主题 CSS
  4. css-inline 把所有 CSS 内联到每个 HTML 标签

微信公众号会剥离 <style> 和 class 属性，所以必须内联。
"""

import os
import re
import markdown
import css_inline
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.formatters import HtmlFormatter

THEMES_DIR = os.path.join(os.path.dirname(__file__), "themes")

# 可用主题列表
AVAILABLE_THEMES = {
    "default": "默认",
    "elegant": "优雅",
    "minimal": "极简黑",
    "grace": "雅致",
    "modern": "现代",
    "warm": "暖色",
    "green": "绿意",
    "red": "红绯",
}

# 可用代码高亮主题（独立于文档主题）
# 参考 wechat.jeffjade.com 的代码风格列表，映射到 Pygments 样式
AVAILABLE_CODE_THEMES: dict[str, dict] = {
    "atom-one-dark":  {"label": "Atom One Dark",  "pygments": "one-dark",      "bg": "#282c34", "color": "#abb2bf"},
    "atom-one-light": {"label": "Atom One Light", "pygments": "friendly",      "bg": "#fafafa", "color": "#383a42"},
    "monokai":        {"label": "Monokai",        "pygments": "monokai",       "bg": "#272822", "color": "#f8f8f2"},
    "github":         {"label": "GitHub",         "pygments": "default",       "bg": "#f8f8f8", "color": "#333333"},
    "vs2015":         {"label": "VS 2015",        "pygments": "native",        "bg": "#1e1e1e", "color": "#dcdcdc"},
    "xcode":          {"label": "Xcode",          "pygments": "xcode",         "bg": "#ffffff", "color": "#000000"},
}

DEFAULT_CODE_THEME = "atom-one-dark"


def _load_theme_css(theme: str) -> str:
    """加载主题 CSS 文件"""
    css_path = os.path.join(THEMES_DIR, f"{theme}.css")
    if not os.path.exists(css_path):
        css_path = os.path.join(THEMES_DIR, "default.css")
    with open(css_path, "r", encoding="utf-8") as f:
        return f.read()


def _highlight_code_blocks(html: str, code_theme: str = DEFAULT_CODE_THEME) -> str:
    """
    找到 <pre><code class="language-xxx"> 块，
    用 Pygments 重新渲染成带内联样式的高亮 HTML。

    code_theme: 代码高亮主题 key（如 "atom-one-dark"）。
    """
    theme_config = AVAILABLE_CODE_THEMES.get(code_theme, AVAILABLE_CODE_THEMES[DEFAULT_CODE_THEME])
    pygments_style = theme_config["pygments"]
    bg = theme_config["bg"]

    pattern = re.compile(
        r'<pre><code(?:\s+class="language-(\w+)")?>(.*?)</code></pre>',
        re.DOTALL,
    )

    def replacer(match):
        lang = match.group(1)
        code = match.group(2)
        # 还原 HTML 实体
        code = (
            code.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )

        try:
            if lang:
                lexer = get_lexer_by_name(lang, stripall=True)
            else:
                lexer = guess_lexer(code)
        except Exception:
            lexer = TextLexer()

        # noclasses=True → 直接生成内联样式，不依赖 CSS class
        formatter = HtmlFormatter(
            noclasses=True,
            style=pygments_style,
            nowrap=False,
            prestyles=(
                f"background: {bg}; padding: 16px; border-radius: 6px; "
                f"overflow-x: auto; font-size: 14px; line-height: 1.6;"
            ),
        )
        return highlight(code, lexer, formatter)

    return pattern.sub(replacer, html)


def _apply_theme_decorations(html: str, theme: str) -> str:
    """
    为特定主题注入装饰性 HTML 元素。
    微信会剥离 CSS class 和伪元素，所以装饰效果必须内联到 HTML 中。
    """
    if theme == "minimal":
        # 极简黑 h3：黑底白字标签需要居中（inline-block 无法自身居中，包一层 div）
        html = re.sub(
            r"<h3>(.*?)</h3>",
            lambda m: (
                f'<div style="text-align: center; margin: 32px 0 12px;"><h3 style="margin: 0;">{m.group(1)}</h3></div>'
            ),
            html,
        )
    return html


def _extract_title_and_summary(md_text: str) -> tuple[str, str]:
    """从 Markdown 中提取标题（第一个 # 标题）和摘要（第一段正文）"""
    title = ""
    summary = ""

    for line in md_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("# ") and not title:
            title = line.lstrip("# ").strip()
        elif not line.startswith("#") and not summary and title:
            # 去掉 markdown 格式
            summary = re.sub(r"[*_`\[\]()]", "", line).strip()
            if len(summary) > 120:
                summary = summary[:117] + "..."
            break

    return title, summary


def md_to_wechat_html(
    md_text: str,
    theme: str = "default",
    code_theme: str = DEFAULT_CODE_THEME,
    serif: bool = True,
) -> dict:
    """
    将 Markdown 转换为微信公众号兼容的 HTML。

    参数:
        theme: 文档主题（排版、字体、颜色）
        code_theme: 代码高亮主题（独立于文档主题）
        serif: 是否使用衬线字体（默认开启）

    返回 {
        "html": str,      # 内联样式的完整 HTML
        "title": str,      # 提取的标题
        "summary": str,    # 提取的摘要
    }
    """
    # 0. 预处理
    # 去掉 Unsplash credit 行（保留图片本身，后续上传到微信）
    md_text = re.sub(r"\*Photo by.*?Unsplash\*\n?", "", md_text)
    # 去掉一级标题（微信会单独显示 title 字段，正文不需要重复）
    md_text = re.sub(r"^# .+\n?", "", md_text, count=1)

    # 修复表格格式：确保表格行前后有空行，分隔行格式规范
    lines = md_text.split("\n")
    fixed_lines = []
    for i, line in enumerate(lines):
        # 修复分隔行：|---|---| → | --- | --- |
        if re.match(r"^\|[-:| ]+\|$", line.strip()) and "-" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            line = "| " + " | ".join(cells) + " |"
        # 确保表格第一行前面有空行
        if line.strip().startswith("|") and i > 0 and fixed_lines and fixed_lines[-1].strip() and not fixed_lines[-1].strip().startswith("|"):
            fixed_lines.append("")
        fixed_lines.append(line)
        # 确保表格最后一行后面有空行
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith("|"):
            fixed_lines.append("")
    md_text = "\n".join(fixed_lines)

    # 1. 提取元信息
    title, summary = _extract_title_and_summary(md_text)

    # 2. Markdown → HTML
    md = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "codehilite",
            "sane_lists",
        ],
        extension_configs={
            "codehilite": {
                "use_pygments": False,  # 我们自己处理高亮
            },
        },
    )
    html_body = md.convert(md_text)

    # 3. 代码高亮（Pygments 内联样式，代码主题独立于文档主题）
    html_body = _highlight_code_blocks(html_body, code_theme=code_theme)

    # 3.5 主题装饰：用 HTML 注入伪元素无法实现的装饰效果
    html_body = _apply_theme_decorations(html_body, theme)

    # 4. 加载主题 CSS + 字体覆盖 + 内联
    theme_css = _load_theme_css(theme)

    # 字体切换：主题默认衬线，关闭时切回无衬线
    if not serif:
        theme_css += """
body, p, li, blockquote, td, th, h1, h2, h3 {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif !important;
}
"""

    full_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>{theme_css}</style></head>
<body>{html_body}</body>
</html>"""

    # css-inline 把 <style> 内容内联到每个标签的 style 属性
    inlined_html = css_inline.inline(full_html)

    # 5. 只取 <body> 内容（微信编辑器只需要正文）
    # css-inline 会给 <body> 加 style 属性，所以用宽松匹配
    body_match = re.search(r"<body[^>]*>(.*)</body>", inlined_html, re.DOTALL)
    body_html = body_match.group(1).strip() if body_match else inlined_html

    return {
        "html": body_html,
        "title": title,
        "summary": summary,
    }
