from typing import TypedDict, Literal, NotRequired

# 支持的平台类型
Platform = Literal["wechat", "xiaohongshu", "zhihu"]


class AgentState(TypedDict):
    """
    贯穿所有节点的共享状态。
    每个节点只负责填充自己那部分，数据自动向下游传递。

    数据流向：
      planner       → 填 keywords
      researcher    → 填 raw_materials, context
      writer        → 填 draft（含 [IMAGE:...] 占位符）
      image_fetcher → 填 images, final_article
    """
    topic: str                   # 用户输入的主题
    platform: Platform           # 目标平台
    direction: str               # 内容方向（预设 key 或自定义描述）
    keywords: list[str]          # Planner 拆解的搜索关键词
    raw_materials: list[str]     # 搜索到的原始素材（每条一个字符串）
    context: str                 # 整理后的素材摘要（喂给 Writer）
    draft: str                   # 初稿，含 [IMAGE: 英文关键词] 占位符
    images: dict[str, str]       # { "[IMAGE: xxx]": "![alt](url)\n*credit*" }
    final_article: str           # 替换图片占位符后的最终文章
    log: list[str]               # 运行日志，供前端侧边栏展示
    history_context: str         # 从向量库检索到的历史素材
    critic_score: int            # Critic 评分（1~10）
    critic_feedback: str         # Critic 修改建议
    retry_count: int             # 重写次数（最多 2 次）
    image_style: NotRequired[str]  # 图片风格预设（可选）