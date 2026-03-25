from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.tools.search import search
from agent.llm import get_llm

llm = get_llm()


def researcher_node(state: AgentState) -> dict:
    """
    对每个关键词执行搜索，然后让模型去重提炼成素材摘要。
    两步走：
      1. 搜索原始数据（Tavily）
      2. LLM 整理提炼（去重 + 结构化）
    """
    retry_count = state.get("retry_count", 0)
    critic_feedback = state.get("critic_feedback", "")

    if retry_count > 0 and critic_feedback:
        print(f"\n[Researcher] 根据 Critic 反馈补充搜索（第 {retry_count + 1} 轮）...")
        print(f"  Critic 建议：{critic_feedback[:80]}")
    else:
        print("\n[Researcher] 开始搜索素材...")

    # Step 0: 从向量库检索历史相关素材
    from agent.memory import search_similar
    history_items = search_similar(state["topic"], k=3)
    history_context = ""
    if history_items:
        history_context = "\n\n---\n\n".join(history_items)
        print(f"  📚 从素材库找到 {len(history_items)} 条历史素材")

    raw_materials: list[str] = state.get("raw_materials", []) if retry_count > 0 else []
    logs: list[str] = []

    # Step 1: 逐个关键词搜索
    for keyword in state["keywords"]:
        print(f"  搜索：{keyword}")
        results = search(keyword, max_results=4)

        for r in results[:3]:  # 每个关键词取前3条
            raw_materials.append(
                f"标题：{r.get('title', '无标题')}\n"
                f"内容：{r.get('content', '')}\n"
                f"来源：{r.get('url', '')}"
            )

        logs.append(f"📰 \"{keyword}\" 找到 {len(results)} 条结果")

    print(f"  共收集 {len(raw_materials)} 条原始素材，开始提炼...")

    # Step 2: LLM 整理提炼，控制 token 消耗
    # 只取前 6000 字的原始素材，避免超出上下文
    joined = "\n\n---\n\n".join(raw_materials)
    if len(joined) > 6000:
        joined = joined[:6000] + "\n\n[内容过长，已截断]"

    summary_res = llm.invoke([
        SystemMessage(content=(
            "你是信息整理助手。请对以下搜索结果进行整理：\n"
            "1. 去掉重复信息\n"
            "2. 提炼核心要点\n"
            "3. 保留具体数据、案例、人名、产品名\n"
            "4. 输出结构清晰的素材摘要，500字以内\n"
            "直接输出摘要内容，不要加前缀说明。"
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
        "raw_materials": raw_materials,
        "context": context,
        "history_context": history_context,
        "log": state.get("log", [])
            + (["📚 从素材库找到历史相关素材"] if history_context else [])
            + logs
            + ["✅ 素材整理完成"],
    }