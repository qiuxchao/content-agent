from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.llm import get_llm
from agent.prompts.templates import get_direction_text

PLANNER_SYSTEM = """你是一位资深内容策划，负责分析选题并规划文章框架。

## 你的任务
结合用户给出的文章主题和预搜索获取的实时资讯，产出一份清晰的文章规划，包括：
- **切入角度**：这篇文章要表达什么核心观点或叙事线（不是泛泛而谈）
- **目标读者**：谁会看这篇文章，他们最关心什么
- **核心要点**：2~4 个要覆盖的关键内容模块，每个说明需要什么素材支撑（数据、案例、对比等）
- **差异化**：这篇文章和普通报道/搬运相比，独特价值在哪

## 重要
- 充分利用提供的搜索结果中的实时信息来指导规划
- 确保规划基于真实的最新资讯，而非猜测

## 输出格式
直接输出规划内容（纯文本），不要加 JSON 包裹，不要加前缀说明。
控制在 200 字以内，简明扼要。"""

PLATFORM_STYLE = {
    "wechat": (
        "公众号推文：1500~2500字，标题关键词前置（50字内），> blockquote 开场点明核心观点，"
        "## 分节展开，善用表格对比和代码块，语气 informative + opinionated，结尾互动引导评论。"
    ),
    "xiaohongshu": (
        "小红书笔记：400~600字，emoji 标题（25字内），开门见山说结论，"
        "3~5个干货要点，口语化表达，结尾带 #标签。"
    ),
    "zhihu": (
        "知乎文章：1000~2000字，标题有观点锋芒，> blockquote 亮观点，"
        "## 分节用论据支撑，理性克制有独立见解，善用表格和引用。"
    ),
}


def planner_node(state: AgentState) -> dict:
    """
    分析主题，规划文章框架和角度。
    输出 outline 供 researcher/writer/critic 参考。
    """
    print("\n[Planner] 分析选题，规划文章框架...")

    direction_text = get_direction_text(state.get("direction", "tech"))
    platform = state["platform"]
    style_hint = PLATFORM_STYLE.get(platform, "")

    # 构建用户消息，包含预搜索结果
    user_parts = [
        f"文章主题：{state['topic']}",
        f"目标平台：{platform}",
        f"平台风格：{style_hint}",
        f"内容方向：{direction_text}",
    ]

    # 注入预搜索素材，让规划有据可依
    raw_materials = state.get("raw_materials", [])
    if raw_materials:
        materials_text = "\n\n".join(raw_materials[:4])
        if len(materials_text) > 3000:
            materials_text = materials_text[:3000] + "\n[已截断]"
        user_parts.append(f"\n## 预搜索获取的实时资讯\n{materials_text}")

    history_context = state.get("history_context", "")
    if history_context:
        user_parts.append(f"\n## 历史相关素材\n{history_context[:1500]}")

    res = get_llm().invoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content="\n".join(user_parts)),
    ])

    outline = res.content.strip()
    print(f"  规划完成（{len(outline)}字）")

    return {
        "outline": outline,
        "log": state.get("log", []) + ["📋 文章规划完成"],
    }
