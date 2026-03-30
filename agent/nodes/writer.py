from langchain_core.messages import HumanMessage
from agent.state import AgentState
from agent.prompts.templates import build_prompt
from agent.llm import get_llm
from agent.config import get_config


def _get_image_mode() -> str:
    """根据 IMAGE_PROVIDER 配置决定插图模式"""
    provider = get_config("IMAGE_PROVIDER").lower()
    if provider == "screenshot":
        return "screenshot"
    if provider == "mixed":
        return "mixed"
    return "image"


def writer_node(state: AgentState) -> dict:
    """
    根据平台 Prompt 模板和素材生成初稿。
    初稿中包含 [IMAGE: 英文关键词] 或 [SCREENSHOT: url, 描述] 占位符，
    由后续的 image_fetcher_node 替换成真实图片。
    """
    print(f"\n[Writer] 开始写作（平台：{state['platform']}）...")

    image_mode = _get_image_mode()
    prompt = build_prompt(
        platform=state["platform"],
        topic=state["topic"],
        context=state["context"],
        direction=state.get("direction", ""),
        outline=state.get("outline", ""),
        image_mode=image_mode,
    )

    try:
        res = get_llm().invoke([HumanMessage(content=prompt)])
        draft = res.content.strip()
    except TypeError as e:
        if "null value for 'choices'" in str(e):
            print("  ⚠️ LLM 返回空响应（可能触发内容审核），正在重试...")
            res = get_llm().invoke([HumanMessage(content=prompt)])
            draft = res.content.strip()
        else:
            raise

    # 统计占位符数量，方便调试
    import re
    image_count = len(re.findall(r"\[IMAGE:", draft))
    screenshot_count = len(re.findall(r"\[SCREENSHOT:", draft))
    total = image_count + screenshot_count

    mode_label = {"screenshot": "截图", "mixed": "混合", "image": "AI 生图"}.get(image_mode, image_mode)
    detail = f"AI 生图 {image_count}" if image_count else ""
    if screenshot_count:
        detail = f"{detail + '，' if detail else ''}截图 {screenshot_count}"
    print(f"  初稿完成（{len(draft)}字，插图模式：{mode_label}，占位符 {total} 个：{detail}）")

    return {
        "draft": draft,
        "log": state.get("log", []) + [
            f"✍️ {state['platform']} 初稿完成（{len(draft)}字）"
        ],
    }