import json
import re
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.llm import get_llm
from agent.prompts.templates import WRITING_PRINCIPLES

CRITIC_SYSTEM = """你是一位资深内容编辑，负责评估文章质量并给出改进建议。

## 重要前提
文章中的数据、版本号、产品名称、评测分数等均来自实时网络搜索的素材（见下方【搜索素材】）。
**不要用你自己的知识去否定文章中的具体数据和事实。**
只在文章与素材明显矛盾、或文章内部前后数据不一致时才扣"内容准确性"分。

## 评分标准（满分 10 分）
1. **内容准确性**（2分）：文章引用的数据是否与素材一致，内部是否自洽
2. **结构完整性**（2分）：开头/正文/结尾是否完整，逻辑是否通顺
3. **平台适配度**（2分）：语气、字数、格式是否符合目标平台风格
4. **可读性**（2分）：表达是否流畅，是否有吸引力
5. **信息密度**（2分）：内容是否充实，有没有空洞或注水

{writing_principles}

## 输出格式
严格输出以下 JSON，不要输出任何其他内容：
```json
{{"score": <1到10的整数>, "feedback": "<具体的修改建议，100字以内>"}}
```"""

CRITIC_USER = """## 目标平台：{platform}

## 主题：{topic}

## 文章规划（Planner 产出）
{outline}

## 搜索素材（Writer 的输入）
{context}

{history_section}

## 文章初稿（需要评估的内容）
{draft}"""


def critic_node(state: AgentState) -> dict:
    """
    给 Writer 的初稿打分。
    提供搜索素材和历史素材作为上下文，确保评估基于充分信息。
    返回 score（1~10）和 feedback（修改建议）。
    """
    retry_count = state.get("retry_count", 0)
    print(f"\n[Critic] 评估初稿（第 {retry_count + 1} 次）...")

    # 构建历史素材部分（如果有）
    history_context = state.get("history_context", "")
    history_section = ""
    if history_context:
        history_section = f"## 历史素材（RAG 召回）\n{history_context}"

    system = CRITIC_SYSTEM.format(writing_principles=WRITING_PRINCIPLES)
    user = CRITIC_USER.format(
        platform=state["platform"],
        topic=state["topic"],
        outline=state.get("outline", "（无规划）"),
        context=state.get("context", ""),
        history_section=history_section,
        draft=state["draft"],
    )

    res = get_llm().invoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])
    raw = res.content.strip()

    # 解析 JSON — 提取最外层 {}
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            score = int(parsed.get("score", 7))
            feedback = str(parsed.get("feedback", ""))
        except (json.JSONDecodeError, ValueError, TypeError):
            score = 7
            feedback = "评分解析失败，默认通过"
    else:
        score = 7
        feedback = "评分解析失败，默认通过"

    score = max(1, min(10, score))

    print(f"  评分：{score}/10")
    if feedback:
        print(f"  建议：{feedback[:80]}...")

    return {
        "critic_score": score,
        "critic_feedback": feedback,
        "log": state.get("log", []) + [
            f"📝 Critic 评分：{score}/10 —— {feedback[:50]}"
        ],
    }
