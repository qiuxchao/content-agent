"""
SQLite 数据库 —— 存储主题和文章记录

表结构：
  topics   — 用户输入的主题（一个主题可以生成多个平台的文章）
  articles — 每个平台对应一篇文章，关联到 topic
"""

import os
import sqlite3
import time
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "content-agent.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """创建表（如果不存在）"""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'tech',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                content_md TEXT NOT NULL DEFAULT '',
                score INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'draft',
                wechat_media_id TEXT DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_articles_topic ON articles(topic_id);
        """)


# ─── Topic CRUD ─────────────────────────────────────────

def create_topic(title: str, direction: str = "tech") -> dict:
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO topics (title, direction, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, direction, now, now),
        )
        topic_id = cur.lastrowid
    return get_topic(topic_id)


def get_topic(topic_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        if not row:
            return None
        topic = dict(row)
        articles = conn.execute(
            "SELECT * FROM articles WHERE topic_id = ? ORDER BY platform",
            (topic_id,),
        ).fetchall()
        topic["articles"] = [dict(a) for a in articles]
    return topic


def list_topics(limit: int = 50, offset: int = 0) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT t.*, COUNT(a.id) as article_count
               FROM topics t LEFT JOIN articles a ON a.topic_id = t.id
               GROUP BY t.id ORDER BY t.updated_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_topic(topic_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        return cur.rowcount > 0


# ─── Article CRUD ───────────────────────────────────────

def create_article(topic_id: int, platform: str, content_md: str = "", score: int = 0) -> dict:
    now = int(time.time())
    with get_conn() as conn:
        # 更新 topic 的 updated_at
        conn.execute("UPDATE topics SET updated_at = ? WHERE id = ?", (now, topic_id))
        cur = conn.execute(
            """INSERT INTO articles (topic_id, platform, content_md, score, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'draft', ?, ?)""",
            (topic_id, platform, content_md, score, now, now),
        )
        return dict(conn.execute("SELECT * FROM articles WHERE id = ?", (cur.lastrowid,)).fetchone())


def update_article(article_id: int, content_md: str | None = None, score: int | None = None, status: str | None = None, wechat_media_id: str | None = None) -> dict | None:
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            return None
        updates = []
        params = []
        if content_md is not None:
            updates.append("content_md = ?")
            params.append(content_md)
        if score is not None:
            updates.append("score = ?")
            params.append(score)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if wechat_media_id is not None:
            updates.append("wechat_media_id = ?")
            params.append(wechat_media_id)
        if updates:
            updates.append("updated_at = ?")
            params.append(now)
            params.append(article_id)
            conn.execute(f"UPDATE articles SET {', '.join(updates)} WHERE id = ?", params)
            conn.execute("UPDATE topics SET updated_at = ? WHERE id = ?", (now, row["topic_id"]))
        return dict(conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone())


def delete_article(article_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        return cur.rowcount > 0


def get_article(article_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return dict(row) if row else None


def find_article(topic_id: int, platform: str) -> dict | None:
    """查找某主题下某平台的文章"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE topic_id = ? AND platform = ?",
            (topic_id, platform),
        ).fetchone()
        return dict(row) if row else None


# 启动时自动建表
init_db()
