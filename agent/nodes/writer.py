from langchain_core.messages import HumanMessage
from agent.state import AgentState
from agent.prompts.templates import build_prompt
from agent.llm import get_llm


def writer_node(state: AgentState) -> dict:
    """
    根据平台 Prompt 模板和素材生成初稿。
    初稿中包含 [IMAGE: 英文关键词] 占位符，
    由后续的 image_fetcher_node 替换成真实图片。
    """
    print(f"\n[Writer] 开始写作（平台：{state['platform']}）...")

    prompt = build_prompt(
        platform=state["platform"],
        topic=state["topic"],
        context=state["context"],
        direction=state.get("direction", ""),
        outline=state.get("outline", ""),
    )

    res = get_llm().invoke([HumanMessage(content=prompt)])
    draft = res.content.strip()

    # 统计占位符数量，方便调试
    import re
    image_count = len(re.findall(r"\[IMAGE:", draft))

    print(f"  初稿完成（{len(draft)}字，含 {image_count} 个插图占位符）")

    return {
        "draft": draft,
        "log": state.get("log", []) + [
            f"✍️ {state['platform']} 初稿完成（{len(draft)}字）"
        ],
    }