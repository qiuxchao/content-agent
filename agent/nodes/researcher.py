import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.tools.search import search
from agent.llm import get_llm


def _extract_keywords(state: AgentState) -> list[str]:
    """
    根据主题和文章规划，拆解出 2~4 个搜索关键词。
    重试时会参考 critic 反馈调整搜索方向。
    """
    retry_count = state.get("retry_count", 0)
    critic_feedback = state.get("critic_feedback", "")

    system = (
        "你是信息检索专家。根据文章主题和规划，拆解出 2 个最佳搜索关键词，用于搜索最新资讯。\n"
        "关键词要具体精准，覆盖不同维度（如：产品本身、竞品对比、行业影响）。\n"
        "直接返回 JSON 数组，不要包含任何其他内容。\n"
        '格式：["关键词1", "关键词2"]'
    )

    user_parts = [
        f"文章主题：{state['topic']}",
        f"目标平台：{state['platform']}",
    ]
    outline = state.get("outline", "")
    if outline:
        user_parts.append(f"文章规划：{outline}")
    if retry_count > 0 and critic_feedback:
        user_parts.append(f"上一轮 Critic 反馈（请针对性补充搜索）：{critic_feedback}")

    res = get_llm().invoke([
        SystemMessage(content=system),
        HumanMessage(content="\n".join(user_parts)),
    ])

    try:
        text = res.content.strip().replace("```json", "").replace("```", "")
        # 提取 JSON 数组
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            keywords = json.loads(match.group())
            if isinstance(keywords, list) and keywords:
                return [str(k) for k in keywords]
    except (json.JSONDecodeError, ValueError):
        pass

    return [state["topic"]]


def researcher_node(state: AgentState) -> dict:
    """
    1. 拆解搜索关键词（基于主题+规划+critic反馈）
    2. 对每个关键词执行搜索
    3. LLM 去重提炼成素材摘要
    """
    retry_count = state.get("retry_count", 0)
    critic_feedback = state.get("critic_feedback", "")

    if retry_count > 0 and critic_feedback:
        print(f"\n[Researcher] 根据 Critic 反馈补充搜索（第 {retry_count + 1} 轮）...")
        print(f"  Critic 建议：{critic_feedback[:80]}")
    else:
        print("\n[Researcher] 开始搜索素材...")

    # Step 0: 拆解搜索关键词（基于 planner 的 outline）
    keywords = _extract_keywords(state)
    print(f"  关键词：{keywords}")

    # 历史素材已在 pre_researcher 中检索，直接复用
    history_context = state.get("history_context", "")

    logs: list[str] = []
    new_materials: list[str] = []

    # Step 1: 逐个关键词搜索（基于 outline 的精准补充搜索）
    for keyword in keywords:
        print(f"  搜索：{keyword}")
        results = search(keyword, max_results=4)

        for r in results:
            new_materials.append(
                f"标题：{r.get('title', '无标题')}\n"
                f"内容：{r.get('content', '')}\n"
                f"来源：{r.get('url', '')}"
            )

        logs.append(f"📰 \"{keyword}\" 找到 {len(results)} 条结果")

    # 合并素材：新搜索 + 预搜索/上轮素材
    old_materials: list[str] = state.get("raw_materials", [])
    raw_materials = new_materials + old_materials

    print(f"  共收集 {len(raw_materials)} 条原始素材（新 {len(new_materials)} 条），开始提炼...")

    # Step 3: LLM 整理提炼
    joined = "\n\n---\n\n".join(raw_materials)
    if len(joined) > 12000:
        joined = joined[:12000] + "\n\n[内容过长，已截断]"

    summary_res = get_llm().invoke([
        SystemMessage(content=(
            "你是信息整理助手。请对以下搜索结果进行整理：\n"
            "1. 合并重复信息（同一事实只保留信息最完整的版本）\n"
            "2. 保留所有具体数据（数字、百分比、价格、日期、版本号）\n"
            "3. 保留所有人名、公司名、产品名、技术术语\n"
            "4. 保留有价值的直接引语和关键表述\n"
            "5. 保留来源 URL（写作时可用于引用）\n"
            "6. 输出结构清晰的素材摘要，1000~1500字\n"
            "宁可多保留信息，也不要过度压缩。直接输出摘要内容，不要加前缀说明。"
        )),
        HumanMessage(content=(
            f"文章主题：{state['topic']}\n\n"
            + (f"上一轮写作的修改建议：{critic_feedback}\n请特别补充相关内容。\n\n" if critic_feedback and retry_count > 0 else "")
            + (f"历史相关素材（来自素材库）：\n{history_context}\n\n" if history_context else "")
            + f"新搜索结果：\n{joined}"
        )),
    ])

    context = summary_res.content.strip()
    print(f"  素材摘要完成（{len(context)}字）")

    return {
        "keywords": keywords,
        "raw_materials": raw_materials,
        "context": context,
        "log": state.get("log", [])
            + [f"🔍 补充搜索关键词：{'、'.join(keywords)}"]
            + logs
            + ["✅ 素材整理完成"],
    }
