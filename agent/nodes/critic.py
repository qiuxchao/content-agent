import json
import re
from langchain_core.messages import HumanMessage
from agent.state import AgentState
from agent.llm import get_llm

llm = get_llm()

CRITIC_PROMPT = """你是一位资深内容编辑，负责评估文章质量。

## 目标平台：{platform}

## 评分标准（满分 10 分）：
1. **内容准确性**（2分）：事实是否正确，数据是否可靠
2. **结构完整性**（2分）：开头/正文/结尾是否完整，逻辑是否通顺
3. **平台适配度**（2分）：语气、字数、格式是否符合目标平台风格
4. **可读性**（2分）：表达是否流畅，是否有吸引力
5. **信息密度**（2分）：内容是否充实，有没有空洞或注水

## 文章初稿：
{draft}

## 请严格按以下 JSON 格式返回，不要输出其他内容：
{{
  "score": <1到10的整数>,
  "feedback": "<具体的修改建议，说明哪里需要改进，100字以内>"
}}
"""


def critic_node(state: AgentState) -> dict:
    """
    给 Writer 的初稿打分。
    返回 score（1~10）和 feedback（修改建议）。
    Graph 根据 score 决定是否回到 Researcher 重写。
    """
    retry_count = state.get("retry_count", 0)
    print(f"\n[Critic] 评估初稿（第 {retry_count + 1} 次）...")

    prompt = CRITIC_PROMPT.format(
        platform=state["platform"],
        draft=state["draft"],
    )

    res = llm.invoke([HumanMessage(content=prompt)])
    raw = res.content.strip()

    # 尝试解析 JSON（模型有时会包裹在 ```json ``` 里）
    json_match = re.search(r"\{[^}]+\}", raw, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            score = int(parsed.get("score", 7))
            feedback = parsed.get("feedback", "")
        except (json.JSONDecodeError, ValueError):
            score = 7  # 解析失败默认通过
            feedback = "评分解析失败，默认通过"
    else:
        score = 7
        feedback = "评分解析失败，默认通过"

    # 限制在 1~10
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
