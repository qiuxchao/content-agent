import json
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.llm import get_llm

llm = get_llm()


def planner_node(state: AgentState) -> dict:
    """
    把用户主题拆解成 2~4 个搜索关键词。
    temperature 用 0.3，让输出更稳定。
    """
    print("\n[Planner] 拆解搜索关键词...")

    res = llm.invoke([
        SystemMessage(content=(
            "你是信息检索专家。"
            "将用户给出的文章主题，拆解成2~4个最佳搜索关键词，用于搜索最新资讯。"
            "直接返回 JSON 数组，不要包含任何其他内容。"
            "格式示例：[\"关键词1\", \"关键词2\", \"关键词3\"]"
        )),
        HumanMessage(content=(
            f"文章主题：{state['topic']}\n"
            f"目标平台：{state['platform']}\n"
            f"内容方向：{state.get('direction', 'tech')}"
        )),
    ])

    # 解析 JSON，容错处理
    try:
        text = res.content.strip().replace("```json", "").replace("```", "")
        keywords: list[str] = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        print(f"  [Planner] JSON 解析失败，回退到原始主题")
        keywords = [state["topic"]]

    print(f"  关键词：{keywords}")

    return {
        "keywords": keywords,
        "log": state.get("log", []) + [f"🔍 搜索关键词：{'、'.join(keywords)}"],
    }