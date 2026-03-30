from agent.state import Platform

# ─────────────────────────────────────────────────────────
# 内容方向预设 + 平台 Prompt 模板
#
# 设计原则：
#   "方向"决定写什么（角色、受众、用词风格）
#   "平台"决定怎么写（结构、字数、格式）
#   两者正交组合，互不耦合
#
# 约定：
#   {topic}     → 用户输入的主题
#   {context}   → Researcher 整理好的素材摘要
#   {direction} → 内容方向描述（预设或自定义）
#   [IMAGE: 英文关键词] → ImageFetcher 自动替换（AI 生图/Unsplash）
#   [SCREENSHOT: url, 描述] → ImageFetcher 自动截图（Playwright）
#
# 标题公式：
#   颠覆式 / 方案式 / 悬念式 / 数字式
#   对比式 / 结果前置 / 反问式 / 共情式
# ─────────────────────────────────────────────────────────

# ── 内容方向预设 ──────────────────────────────────────────
# key 是前端传的 direction_id，value 是注入 Prompt 的角色描述
DIRECTION_PRESETS: dict[str, dict] = {
    "tech": {
        "label": "科技 / AI",
        "desc": "科技资讯、AI 动态、产品评测",
        "role": "你是一位资深科技自媒体作者，写作风格：informative、opinionated、not dry。你的文章信息密度高，善用表格对比和代码示例，对技术趋势有自己的判断，不做信息搬运工。关注 AI、开发工具、开源项目、互联网产品。",
    },
    "finance": {
        "label": "财经 / 商业",
        "desc": "商业分析、投资趋势、行业洞察",
        "role": "你是一位财经领域的资深内容创作者，擅长用通俗的语言解读商业逻辑和市场趋势。你的文章特点是：有数据支撑、有独到分析、避免信息茧房。",
    },
    "lifestyle": {
        "label": "生活方式",
        "desc": "好物推荐、效率工具、生活技巧",
        "role": "你是一位生活方式博主，擅长分享提升生活品质的方法和好物。你的风格是：真实体验为主、有审美品味、不浮夸不做作。",
    },
    "education": {
        "label": "知识 / 教育",
        "desc": "学习方法、知识科普、职场成长",
        "role": "你是一位知识分享型创作者，擅长把专业知识讲得通俗有趣。你的文章特点是：逻辑清晰、有实例、让读者有'原来如此'的感觉。",
    },
}

# 默认方向
DEFAULT_DIRECTION = "tech"

# ── 通用写作原则 ──────────────────────────────────────────
WRITING_PRINCIPLES = """
【写作原则】
1. 内容准确：所有数据、事实必须来自素材，禁止编造数据
2. 信息密度高：每一段都要有具体信息（数据、案例、人名、产品名），杜绝空话套话
3. 具体胜过抽象："3天完成"比"很快完成"好，"节省60%时间"比"大幅节省时间"好
4. 保留金句：素材中有力的表述和数据要原样保留，不要弱化
5. 每段只讲一件事，段与段之间有清晰的逻辑衔接
6. 有态度有观点：你不是在搬运信息，而是在解读信息。给出你的判断
7. 中文正文，英文专有名词保留原文（如 Claude、GPT-4o、LangChain）
8. 禁止出现：本文介绍、众所周知、随着XX的发展、让我们一起来看、不用多说、在当今时代

【输出格式——极其重要，必须严格遵守】
- 第一行必须是 # 标题（一级标题，用一个 #）
- 标题下面紧跟一行 > 引用，用一句话概括文章核心观点
- 正文中的小节标题用 ## （二级标题）
- 对比性信息（版本、定价、性能、功能）用表格呈现
- 技术相关内容可以适当展示代码块
- 禁止输出任何结构标签，包括但不限于：
  "标题：""开头钩子：""背景：""核心内容：""观点总结""结尾互动"
  这些是给你的写作指导，不是文章内容，绝对不能出现在输出中
- 直接像一篇发表在平台上的完整文章一样输出，读者看到的就是最终稿
- 用 Markdown 格式：# 标题、## 小节、> 引用、**加粗**、列表、表格、代码块等
"""

# ── 平台 Prompt 模板 ──────────────────────────────────────
PLATFORM_PROMPTS: dict[str, str] = {

    "wechat": """{direction}

请根据下方素材，写一篇关于「{topic}」的公众号推文。

【标题要求】
- 50字以内，核心关键词前置
- 使用中文标点（：、——、？）
- 包含具体信息（版本号、数据、关键特性），让标题本身就有信息量
- 好的标题示例：
  · "Harness Engineering：2026 年最值得学的不是 AI，而是给 AI 搭脚手架"
  · "GLM-5.1：国产大模型编程能力首次逼近 Claude Opus 4.6"
  · "Vibe Coding 正在杀死开源"
- 禁止用：震惊、万字长文、建议收藏、深度好文、你绝对想不到

【结构要求】
1. 标题后紧跟一个 > blockquote，用一句话概括核心观点（这是读者最先看到的信息）
2. 用 ## 分成 2~4 个小节，自然展开：
   - 小节标题要具体有信息量，不要用"背景介绍""详细分析"这类空标题
   - 有对比的内容用表格（版本对比、定价对比、性能跑分等）
   - 技术内容适当展示代码块
   - 每个小节有你的解读，不是纯搬运
3. 结尾给出你的独立判断 + 一个具体问题引导评论（如"你在用什么？欢迎留言"）

【格式要求】
- 字数：1500~2500字
- 语气：informative, opinionated, not dry — 有信息量、有态度、不枯燥
- **加粗核心结论和关键数据**
{image_instructions}
""" + WRITING_PRINCIPLES + """
【素材】
{context}
""",

    "xiaohongshu": """{direction}

请根据下方素材，写一篇关于「{topic}」的小红书笔记。

【标题要求】
- emoji + 口语化 + 有具体信息
- 25字以内
- 好的标题举例：
  · "🤯 试了3天这个工具，效率直接翻倍"
  · "💡 别再用XX了！这个方案碾压级好用"
- 禁止用：赶紧收藏、建议码住、太全了

【结构要求】
1. 开门见山：第一句话直接说结论或最惊人的信息
2. 3~5个核心要点，每个要点具体（有功能、效果、数据）
3. 一句真实感受 + 一个互动问题

【格式要求】
- 字数：400~600字
- emoji 适度（每2~3行一个），段落之间空一行
- 结尾另起一行，6~8个 #标签
{image_instructions}
""" + WRITING_PRINCIPLES + """
【素材】
{context}
""",

    "zhihu": """{direction}

请根据下方素材，写一篇关于「{topic}」的知乎文章。

【标题要求】
- 有信息量、有观点锋芒，关键词前置
- 好的标题示例：
  · "为什么 XX 被严重高估了？"
  · "关于 XX，大多数人理解的都是错的"
  · "如何用 XX 解决 YY 问题？一个被低估的方案"
- 禁止用：浅谈、简述、关于XX的思考、XX的探索与实践

【结构要求】
1. 标题后紧跟 > blockquote 亮出核心观点
2. 用 ## 分成 2~4 个小节，用论据（数据、案例、技术分析）支撑观点
3. 适当加入"反驳常见误解"的角度增加深度
4. 结尾给出独立判断，不是复述前文

【格式要求】
- 字数：1000~2000字
- 语气：理性克制，有独立见解，可以有锋芒但不情绪化
- **加粗核心论点和关键数据**
- 对比性信息用表格，引用关键数据用 > 引用格式
{image_instructions}
""" + WRITING_PRINCIPLES + """
【素材】
{context}
""",
}


# ── 插图模式说明（根据 IMAGE_PROVIDER 注入）──────────────
IMAGE_INSTRUCTION = """- 插图：在每个 ## 段落开始前，单独一行写 [IMAGE: 详细的英文绘图提示词]
  提示词必须包含：① 具体的视觉隐喻（与本段内容强关联）② 色彩方案（含 hex 色值）③ 渲染风格
  可以包含文字标注、品牌视觉元素（logo 轮廓、品牌色）、数据可视化。
  ✗ [IMAGE: AI technology]（太抽象）
  ✗ [IMAGE: performance comparison]（没有画面）
  ✓ [IMAGE: A futuristic digital illustration showing a glowing Chinese dragon made of circuit board patterns and code streams, coiling around a large glowing "5.1" number. Blue and gold light emanating outward. Color palette: deep navy (#0A1628), electric blue (#1A73E8), gold (#FFD600). Style: flat vector with cinematic lighting, 16:9]"""

SCREENSHOT_INSTRUCTION = """- 插图：在每个 ## 段落开始前，单独一行写 [SCREENSHOT: 官方网址, 中文描述]
  截图目标必须是与本段内容直接相关的**官方网站、产品页面、文档页面**。
  优先级：① 官方主页 ② 官方文档/发布说明 ③ 产品演示页面
  ✗ [SCREENSHOT: https://google.com, 搜索结果]（不是官方页面）
  ✓ [SCREENSHOT: https://www.anthropic.com/claude, Claude 产品介绍页]
  ✓ [SCREENSHOT: https://glm5.online/, GLM-5 性能基准测试页面]"""

MIXED_INSTRUCTION = """- 插图方式一（截图）：在需要展示**产品界面、官方页面、实际效果**的段落前，单独一行写 [SCREENSHOT: 官方网址, 中文描述]
  截图目标必须是与本段内容直接相关的官方网站、产品页面、文档页面。
  ✓ [SCREENSHOT: https://www.anthropic.com/claude, Claude 产品介绍页]
- 插图方式二（AI 生图）：在需要**概念性、装饰性、数据可视化**插图的段落前，单独一行写 [IMAGE: 详细的英文绘图提示词]
  提示词必须包含具体的视觉隐喻、色彩方案（含 hex 色值）、渲染风格。
  ✓ [IMAGE: A futuristic digital illustration showing neural network nodes connected by glowing pathways. Color palette: deep navy (#0A1628), electric blue (#1A73E8), gold (#FFD600). Style: flat vector with cinematic lighting, 16:9]
- 根据内容特点灵活选择：有官方页面可截的用 SCREENSHOT，需要创意表达的用 IMAGE"""


def get_direction_text(direction: str) -> str:
    """
    获取方向描述文本。
    如果是预设 key（如 "tech"），返回预设的 role；
    否则视为自定义方向描述，直接使用。
    """
    if direction in DIRECTION_PRESETS:
        return DIRECTION_PRESETS[direction]["role"]
    # 自定义方向：用户直接输入的描述
    return f"你是一位专业的内容创作者。你的写作方向是：{direction}"


def _get_image_instruction(image_mode: str) -> str:
    """根据配图模式返回对应的插图说明"""
    if image_mode == "screenshot":
        return SCREENSHOT_INSTRUCTION
    elif image_mode == "mixed":
        return MIXED_INSTRUCTION
    else:
        return IMAGE_INSTRUCTION


def build_prompt(platform: Platform, topic: str, context: str, direction: str = "", outline: str = "", image_mode: str = "image") -> str:
    """用实际内容替换模板中的占位符"""
    if not direction:
        direction = DEFAULT_DIRECTION
    direction_text = get_direction_text(direction)
    template = PLATFORM_PROMPTS[platform]

    # 替换插图说明
    image_instruction = _get_image_instruction(image_mode)
    template = template.replace("{image_instructions}", image_instruction)

    result = (
        template
        .replace("{direction}", direction_text)
        .replace("{topic}", topic)
        .replace("{context}", context)
    )
    # 注入文章规划（如果有）
    if outline:
        result = result.replace("【素材】", f"【文章规划（Planner 产出，请参考但不必死板遵循）】\n{outline}\n\n【素材】")
    return result
