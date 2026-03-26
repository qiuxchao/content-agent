# Content Agent

基于 LangGraph + LangChain 构建的 AI 内容生产 Agent。输入主题，自动搜集资讯、生成多平台文章并配图，支持一键发布到微信公众号草稿箱。

![Content Agent 预览](assets/preview.png)

## 功能

**内容生成**
- 多平台写作：公众号（深度长文）、小红书（种草笔记）、知乎（专业问答），自动适配各平台风格
- 内容方向预设：科技/AI、财经/商业、生活方式、知识/教育，也支持自定义方向和提示词
- 自动搜索素材：Tavily 搜索最新资讯 + LLM 提炼整理
- 质量自检：Critic 节点给初稿打分（满分 10 分），不达标自动重写
- RAG 素材库：历史素材存入本地向量库，写相关主题时自动关联复用
- 自动配图：Unsplash 图片搜索，自动匹配文章内容

**文章管理**
- 主题管理：按主题组织文章，一个主题可生成多个平台版本
- 历史记录：SQLite 本地存储，支持查看、编辑、删除
- 一键复制：生成的文章可直接复制到各平台发布

**微信公众号发布**
- Markdown → 微信 HTML：内置转换器，CSS 自动内联（微信不支持 `<style>` 标签）
- 8 套主题风格：默认、优雅、极简黑、雅致、现代、暖色、绿意、红绯
- 主题预览：支持手机/PC 模式切换预览
- 图片自动上传：正文图片自动上传到微信素材库
- AI 封面提示词：根据文章内容生成封面图绘图 prompt，复制到 ChatGPT / Gemini / 即梦等平台生成

**可观测**
- 接入 LangSmith，每个节点的输入输出、耗时、Token 用量一目了然

## 技术栈

| 层 | 技术 |
|---|---|
| Agent 框架 | LangGraph (Python) |
| LLM | 兼容 OpenAI / Anthropic 规范的任意模型 |
| 搜索 | Tavily Search API |
| 配图 | Unsplash API |
| RAG | Chroma (本地向量库) |
| 数据库 | SQLite (文章管理) |
| HTML 转换 | markdown + Pygments + css-inline |
| API 层 | FastAPI + SSE |
| 前端 | Next.js + Tailwind CSS + Ant Design |
| 可观测 | LangSmith |
| 包管理 | uv (Python) / bun (前端) |

## 项目结构

```
content-agent/
├── agent/                       # Agent 核心
│   ├── graph.py                 # LangGraph 主图（节点 + 条件分支）
│   ├── state.py                 # 共享状态定义（AgentState）
│   ├── llm.py                   # LLM 工厂（支持 OpenAI / Anthropic 规范）
│   ├── memory.py                # RAG 向量库读写（Chroma）
│   ├── db.py                    # SQLite 数据库（主题 + 文章管理）
│   ├── nodes/
│   │   ├── planner.py           # 拆解搜索关键词
│   │   ├── researcher.py        # 搜索 + 检索历史素材 + 提炼
│   │   ├── writer.py            # 按平台 Prompt 生成初稿
│   │   ├── critic.py            # 质量评估 + 修改建议
│   │   └── image_fetcher.py     # Unsplash 配图
│   ├── prompts/
│   │   └── templates.py         # 内容方向预设 + 三平台 Prompt 模板
│   ├── publish/
│   │   ├── wechat_html.py       # Markdown → 微信 HTML（内联样式）
│   │   ├── wechat_api.py        # 微信公众号 API 客户端
│   │   ├── cover_prompt.py      # AI 封面图提示词生成
│   │   └── themes/              # 8 套微信文章主题 CSS
│   └── tools/
│       ├── search.py            # Tavily 搜索
│       └── unsplash.py          # Unsplash 图片搜索
├── api/
│   └── server.py                # FastAPI（SSE 生成 + CRUD + 发布）
├── web/                         # Next.js 前端
│   └── app/
│       ├── page.tsx             # 主页面（三栏布局）
│       ├── theme.ts             # 暖色调主题 token
│       └── components/
│           ├── TopicList.tsx     # 主题历史列表
│           ├── InputPanel.tsx    # 新建主题（方向 + 平台 + 提示词）
│           ├── ArticlePanel.tsx  # 文章渲染 + 复制/发布
│           ├── StatusPanel.tsx   # Agent 运行状态
│           ├── PublishPanel.tsx  # 微信发布（主题预览 + 封面 prompt）
│           └── PlatformIcons.tsx # 微信/小红书/知乎 SVG 图标
├── data/                        # 本地数据（git 忽略）
│   ├── vectorstore/             # Chroma 向量库
│   └── content-agent.db         # SQLite 数据库
├── run.py                       # CLI 入口
├── pyproject.toml
└── .env.example
```

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)（Python 包管理）
- [bun](https://bun.sh)（前端包管理，也可用 npm）

### 1. 克隆项目

```bash
git clone https://github.com/qiuxchao/content-agent.git
cd content-agent
```

### 2. 安装依赖

```bash
# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装 Python 依赖
uv sync

# 安装前端依赖
cd web && bun install && cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入以下配置：

**LLM 配置（支持任意兼容 OpenAI 规范的服务）**

| 变量 | 说明 |
|---|---|
| `LLM_PROVIDER` | `openai`（默认）或 `anthropic` |
| `LLM_API_KEY` | API Key |
| `LLM_BASE_URL` | API 地址，OpenAI 官方可留空 |
| `LLM_MODEL` | 模型名称 |

常用配置示例：

```bash
# Kimi
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL=moonshot-v1-8k

# DeepSeek
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# OpenAI
LLM_MODEL=gpt-4o-mini

# Anthropic Claude（需额外安装：uv add langchain-anthropic）
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
```

**Embedding 配置（RAG 素材库）**

如果 LLM 服务不提供 Embedding API（如 Kimi），需要单独配置：

```bash
# 推荐：硅基流动（免费，中文效果好）
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
EMBEDDING_API_KEY=你的key
```

**其他 Key**

| 变量 | 获取地址 | 必填 |
|---|---|---|
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com)（免费 1000次/月） | 是 |
| `UNSPLASH_ACCESS_KEY` | [unsplash.com/developers](https://unsplash.com/developers)（免费） | 是 |
| `LANGCHAIN_API_KEY` | [smith.langchain.com](https://smith.langchain.com)（免费） | 否 |
| `WECHAT_APP_ID` | [mp.weixin.qq.com](https://mp.weixin.qq.com) → 开发 → 基本配置 | 否 |
| `WECHAT_APP_SECRET` | 同上 | 否 |

### 4. 启动

#### 方式一：Web UI（推荐）

打开两个终端：

```bash
# 终端 1 — Python API
uv run uvicorn api.server:app --reload --port 8917

# 终端 2 — Next.js 前端
cd web && bun dev
```

打开 http://localhost:3917

#### 方式二：命令行

```bash
# 编辑 run.py 顶部的 TOPIC 和 PLATFORM
uv run run.py
```

## Agent 执行流程

```
用户输入主题 + 选择方向和平台
    │
    ▼
[Planner]        拆解 2~4 个搜索关键词
    │
    ▼
[Researcher]     ① 向量库检索历史素材
                 ② Tavily 搜索新素材
                 ③ LLM 整理提炼
    │
    ▼
[Writer]         按方向角色 + 平台 Prompt 生成初稿
    │
    ▼
[Critic]         打分（满分 10）
                 ≥ 7 → 继续
                 < 7 → 回到 Researcher 重写（最多 2 次）
    │
    ▼
[ImageFetcher]   Unsplash 配图替换占位符
    │
    ▼
[SaveMemory]     素材存入向量库
    │
    ▼
文章保存到数据库 → 前端展示
```

## 三平台风格

| | 公众号 | 小红书 | 知乎 |
|---|---|---|---|
| 字数 | 1500~2500 | 400~600 | 1000~2000 |
| 标题 | 数字/悬念/对比式 | emoji + 口语化 | 问题式/观点式 |
| 结构 | H2 分节，逻辑层次 | 分点列举 | 先结论后论据 |
| 语气 | 有温度有观点 | 接地气，干货感 | 理性克制 |

## 自定义

### 内容方向

内置 4 个方向预设（科技/财经/生活/教育），也可以：
- 在前端选"自定义"输入方向描述
- 选预设后点"编辑提示词"微调角色设定
- 在 `agent/prompts/templates.py` 的 `DIRECTION_PRESETS` 中添加新预设

### 微信主题

8 套内置主题，CSS 文件在 `agent/publish/themes/` 目录下，可自行添加或修改。

### 添加新平台

1. `agent/state.py` 的 `Platform` 类型中添加新值
2. `agent/prompts/templates.py` 中添加对应的 Prompt 模板

## 调试

```bash
# .env 中配置 LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=你的key
LANGCHAIN_PROJECT=content-agent
```

访问 [smith.langchain.com](https://smith.langchain.com) 查看完整 Trace。

```bash
# 查看 RAG 向量库内容
uv run inspect_memory.py
```

## License

MIT
