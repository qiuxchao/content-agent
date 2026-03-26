"""
FastAPI 服务 —— SSE 流式生成 + 文章管理 CRUD + 微信发布

启动方式：uv run uvicorn api.server:app --reload --port 8917
"""

import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from fastapi import UploadFile, File, Form

from agent.graph import run_stream
from agent.state import Platform
from agent.prompts.templates import DIRECTION_PRESETS, DEFAULT_DIRECTION
from agent.publish.wechat_api import check_configured as wechat_configured, publish_article
from agent.publish.wechat_html import md_to_wechat_html, AVAILABLE_THEMES
from agent.publish.cover_prompt import generate_cover_prompt
from agent import db

app = FastAPI(title="Content Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3917"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 生成 ───────────────────────────────────────────────

class GenerateRequest(BaseModel):
    topic: str
    platform: Platform
    direction: str = "tech"
    topic_id: Optional[int] = None  # 传了就关联已有主题，不传就新建


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """SSE 流式生成文章，自动保存到数据库"""

    # 创建或复用主题
    if req.topic_id:
        topic_record = db.get_topic(req.topic_id)
    else:
        topic_record = db.create_topic(req.topic, req.direction)

    topic_id = topic_record["id"] if topic_record else None

    def event_stream():
        last_state = {}
        for event in run_stream(req.topic, req.platform, req.direction):
            node = event["node"]
            data = event["data"]
            last_state.update(data)

            payload = {
                "node": node,
                "data": {
                    "log": data.get("log", []),
                    "keywords": data.get("keywords", []),
                    "context": data.get("context", ""),
                    "draft": data.get("draft", ""),
                    "critic_score": data.get("critic_score", 0),
                    "critic_feedback": data.get("critic_feedback", ""),
                    "final_article": data.get("final_article", ""),
                    "retry_count": data.get("retry_count", 0),
                },
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # 保存文章到数据库
        article_md = last_state.get("final_article", "")
        score = last_state.get("critic_score", 0)
        article_record = None

        if topic_id and article_md:
            # 检查是否已有该平台文章，有就更新，没有就新建
            existing = db.find_article(topic_id, req.platform)
            if existing:
                article_record = db.update_article(
                    existing["id"], content_md=article_md, score=score
                )
            else:
                article_record = db.create_article(
                    topic_id, req.platform, article_md, score
                )

        done_payload = {
            "node": "__done__",
            "data": {
                "final_article": article_md,
                "critic_score": score,
                "log": last_state.get("log", []),
                "topic_id": topic_id,
                "article_id": article_record["id"] if article_record else None,
            },
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ─── 主题 CRUD ──────────────────────────────────────────

@app.get("/api/topics")
async def list_topics(limit: int = 50, offset: int = 0):
    return db.list_topics(limit, offset)


@app.get("/api/topics/{topic_id}")
async def get_topic(topic_id: int):
    topic = db.get_topic(topic_id)
    if not topic:
        return {"error": "not found"}
    return topic


@app.delete("/api/topics/{topic_id}")
async def delete_topic(topic_id: int):
    return {"deleted": db.delete_topic(topic_id)}


# ─── 文章 CRUD ──────────────────────────────────────────

class ArticleUpdateRequest(BaseModel):
    content_md: Optional[str] = None
    score: Optional[int] = None
    status: Optional[str] = None


@app.put("/api/articles/{article_id}")
async def update_article(article_id: int, req: ArticleUpdateRequest):
    result = db.update_article(
        article_id,
        content_md=req.content_md,
        score=req.score,
        status=req.status,
    )
    if not result:
        return {"error": "not found"}
    return result


@app.delete("/api/articles/{article_id}")
async def delete_article(article_id: int):
    return {"deleted": db.delete_article(article_id)}


# ─── 方向预设 ───────────────────────────────────────────

@app.get("/api/directions")
async def directions():
    return {
        "default": DEFAULT_DIRECTION,
        "presets": [
            {"key": k, "label": v["label"], "desc": v["desc"]}
            for k, v in DIRECTION_PRESETS.items()
        ],
    }


# ─── 微信发布 ───────────────────────────────────────────

@app.get("/api/publish/wechat/status")
async def wechat_status():
    return {
        "configured": wechat_configured(),
        "themes": [{"key": k, "label": v} for k, v in AVAILABLE_THEMES.items()],
    }


@app.post("/api/publish/wechat/preview")
async def wechat_preview(article: str = Form(...), theme: str = Form("default")):
    """Markdown → 微信 HTML 预览"""
    result = md_to_wechat_html(article, theme=theme)
    return result


class CoverPromptRequest(BaseModel):
    title: str
    summary: str = ""
    direction: str = "tech"


@app.post("/api/publish/cover-prompt")
async def cover_prompt(req: CoverPromptRequest):
    """用 AI 生成封面图绘图提示词"""
    prompt = generate_cover_prompt(req.title, req.summary, req.direction)
    return {"prompt": prompt}


@app.post("/api/publish/wechat")
async def wechat_publish(
    article: str = Form(...),
    theme: str = Form("default"),
    title: str = Form(""),
    summary: str = Form(""),
    author: str = Form(""),
    article_id: Optional[int] = Form(None),
    cover: Optional[UploadFile] = File(None),
):
    """发布到微信公众号草稿箱"""
    import tempfile

    cover_path = ""
    if cover and cover.filename:
        suffix = os.path.splitext(cover.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await cover.read()
            tmp.write(content)
            cover_path = tmp.name

    try:
        result = publish_article(
            md_text=article, theme=theme, title=title,
            summary=summary, author=author, cover_path=cover_path,
        )
        # 更新文章状态
        if article_id:
            db.update_article(
                article_id, status="published",
                wechat_media_id=result.get("media_id", ""),
            )
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if cover_path and os.path.exists(cover_path):
            os.unlink(cover_path)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
