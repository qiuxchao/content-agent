"""
前置搜索节点 —— 在 Planner 之前执行，提供实时信息支撑规划。

职责：
  1. 基于原始 topic 执行搜索，获取实时资讯
  2. 从向量库检索历史素材（RAG）
  3. 将结果存入 state，供 Planner 参考
"""

from agent.state import AgentState
from agent.tools.search import search
from agent.memory import search_similar


def pre_researcher_node(state: AgentState) -> dict:
    """基于主题做初步搜索 + RAG 检索，为 Planner 提供实时信息。"""
    topic = state["topic"]
    print(f"\n[Pre-Researcher] 预搜索：{topic}")

    logs: list[str] = []
    raw_materials: list[str] = []

    # 1. 搜索实时资讯
    results = search(topic, max_results=4)
    for r in results:
        raw_materials.append(
            f"标题：{r.get('title', '无标题')}\n"
            f"内容：{r.get('content', '')}\n"
            f"来源：{r.get('url', '')}"
        )
    logs.append(f"📰 预搜索 \"{topic}\" 找到 {len(results)} 条结果")
    print(f"  搜索到 {len(results)} 条结果")

    # 2. 从向量库检索历史素材
    history_items = search_similar(topic, k=3)
    history_context = ""
    if history_items:
        history_context = "\n\n---\n\n".join(history_items)
        logs.append(f"📚 从素材库找到 {len(history_items)} 条历史素材")
        print(f"  📚 从素材库找到 {len(history_items)} 条历史素材")

    print(f"  预搜索完成，收集 {len(raw_materials)} 条素材")

    return {
        "raw_materials": raw_materials,
        "history_context": history_context,
        "log": state.get("log", []) + logs,
    }
