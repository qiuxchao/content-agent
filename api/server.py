"""
FastAPI 服务 —— 提供 SSE 流式接口给前端。

启动方式：uv run uvicorn api.server:app --reload --port 8000
"""

import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agent.graph import run_stream
from agent.state import Platform
from agent.prompts.templates import DIRECTION_PRESETS, DEFAULT_DIRECTION

app = FastAPI(title="Content Agent API")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3917"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str
    platform: Platform
    direction: str = "tech"  # 预设 key 或自定义描述


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """
    SSE 流式接口。
    每个节点完成时推送一条事件，前端用 EventSource 接收。

    事件格式：
      data: {"node": "planner", "data": {"keywords": [...], "log": [...]}}
      data: {"node": "researcher", "data": {"context": "...", "log": [...]}}
      ...
      data: {"node": "__done__", "data": {"article": "...", "score": 7}}
    """
    def event_stream():
        last_state = {}
        for event in run_stream(req.topic, req.platform, req.direction):
            node = event["node"]
            data = event["data"]
            last_state.update(data)

            # 只推送前端需要的字段，避免发送过大的 raw_materials
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

        # 发送完成信号
        done_payload = {
            "node": "__done__",
            "data": {
                "final_article": last_state.get("final_article", ""),
                "critic_score": last_state.get("critic_score", 0),
                "log": last_state.get("log", []),
            },
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/directions")
async def directions():
    """返回可用的内容方向预设列表"""
    return {
        "default": DEFAULT_DIRECTION,
        "presets": [
            {"key": k, "label": v["label"], "desc": v["desc"]}
            for k, v in DIRECTION_PRESETS.items()
        ],
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}
