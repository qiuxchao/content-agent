import re
from agent.state import AgentState
from agent.tools.unsplash import search_images

# 匹配 [IMAGE: 任意内容]
IMAGE_PATTERN = re.compile(r"\[IMAGE:\s*([^\]]+)\]")


def image_fetcher_node(state: AgentState) -> dict:
    """
    解析初稿中所有 [IMAGE: 关键词] 占位符，
    调用 Unsplash 获取真实图片，替换成 Markdown 图片格式。

    替换后格式：
      ![alt描述](图片URL)
      *Photo by 摄影师 on Unsplash*
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

    image_map: dict[str, str] = {}
    logs: list[str] = []

    for match in matches:
        placeholder = match.group(0)      # 完整占位符，如 [IMAGE: AI robot]
        keyword = match.group(1).strip()  # 关键词，如 AI robot

        # 同一个占位符只处理一次（去重）
        if placeholder in image_map:
            continue

        print(f"  获取图片：{keyword}")
        imgs = search_images(keyword, count=1)

        if imgs:
            img = imgs[0]
            # Markdown 格式，附上 Unsplash 署名（这是 Unsplash 使用协议要求的）
            image_map[placeholder] = (
                f"\n![{img.alt}]({img.url})\n"
                f"*{img.credit}*\n"
            )
            logs.append(f"🖼️ 插图：{keyword}")
        else:
            # 找不到图就把占位符删掉，不影响文章结构
            image_map[placeholder] = ""
            logs.append(f"⚠️ 未找到插图：{keyword}")

    # 把初稿里所有占位符替换成真实图片
    final_article = state["draft"]
    for placeholder, replacement in image_map.items():
        final_article = final_article.replace(placeholder, replacement)

    print(f"  完成，共处理 {len(image_map)} 张插图")

    return {
        "images": image_map,
        "final_article": final_article,
        "log": state.get("log", []) + logs + ["🎉 文章生成完成！"],
    }