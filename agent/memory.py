"""
RAG 素材库 —— 基于 Chroma 的本地向量存储。

功能：
  - save(): 把本次生成的素材存入向量库
  - search(): 用主题检索历史相关素材

数据持久化在 data/vectorstore/ 目录，重启不丢失。
"""

import os
import time
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 向量库存储路径
PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vectorstore")

# Embedding 模型（用和 LLM 相同的 API 配置）
_embeddings = None


def _get_embeddings() -> OpenAIEmbeddings:
    """延迟初始化 Embedding 模型，复用 LLM 的 API 配置。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002"),
            openai_api_key=os.getenv("EMBEDDING_API_KEY", os.getenv("LLM_API_KEY", "")),
            openai_api_base=os.getenv("EMBEDDING_BASE_URL", os.getenv("LLM_BASE_URL", None)),
        )
    return _embeddings


def _get_store() -> Chroma:
    """获取 Chroma 向量库实例。"""
    os.makedirs(PERSIST_DIR, exist_ok=True)
    return Chroma(
        collection_name="content_agent_materials",
        embedding_function=_get_embeddings(),
        persist_directory=PERSIST_DIR,
    )


def save(topic: str, context: str, platform: str) -> None:
    """
    把本次素材存入向量库。
    每次存一条记录：content = 素材摘要，metadata 带主题/平台/时间。
    """
    if not context.strip():
        return

    store = _get_store()
    store.add_texts(
        texts=[context],
        metadatas=[{
            "topic": topic,
            "platform": platform,
            "timestamp": str(int(time.time())),
        }],
    )
    print(f"  💾 素材已存入向量库（{len(context)}字）")


def search_similar(topic: str, k: int = 3) -> list[str]:
    """
    用主题检索历史相关素材，返回最多 k 条。
    如果向量库为空或检索失败，返回空列表（不影响主流程）。
    """
    try:
        store = _get_store()
        # 检查是否有数据
        if store._collection.count() == 0:
            return []

        results = store.similarity_search(topic, k=k)
        return [doc.page_content for doc in results]
    except Exception as e:
        print(f"  ⚠️ 向量库检索失败（不影响主流程）：{e}")
        return []
