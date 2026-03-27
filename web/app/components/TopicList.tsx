"use client";

import { useEffect, useState } from "react";
import { Button, Popconfirm } from "antd";
import { PlusOutlined, DeleteOutlined, LoadingOutlined, SettingOutlined } from "@ant-design/icons";
import { theme } from "../theme";
import type { Platform } from "../page";

const PLATFORM_LABELS: Record<string, string> = {
  wechat: "公众号",
  xiaohongshu: "小红书",
  zhihu: "知乎",
};

const PLATFORM_COLORS: Record<string, string> = {
  wechat: "#07c160",
  xiaohongshu: "#fe2c55",
  zhihu: "#0066ff",
};

interface TopicItem {
  id: number;
  title: string;
  direction: string;
  article_count: number;
  created_at: number;
  updated_at: number;
}

export interface ArticleItem {
  id: number;
  topic_id: number;
  platform: string;
  content_md: string;
  score: number;
  status: string;
  created_at: number;
}

interface TopicDetail {
  id: number;
  title: string;
  direction: string;
  articles: ArticleItem[];
}

interface Props {
  onNewTopic: () => void;
  onSelectArticle: (topicId: number, article: ArticleItem) => void;
  onGenerateForPlatform: (topicId: number, topicTitle: string, direction: string, platform: Platform) => void;
  onViewRunning: () => void; // 切回查看正在生成的主题
  refreshKey: number;
  activeTopicId: number | null;
  activeArticleId: number | null;
  isRunning: boolean;
  runningTopicId: number | null; // 正在生成的主题 ID
  runningPlatform?: string; // 正在生成的平台
  onSettings?: () => void;
}

export function TopicList({
  onNewTopic, onSelectArticle, onGenerateForPlatform, onViewRunning, refreshKey,
  activeTopicId, activeArticleId, isRunning, runningTopicId, runningPlatform, onSettings,
}: Props) {
  const [topics, setTopics] = useState<TopicItem[]>([]);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [topicDetail, setTopicDetail] = useState<TopicDetail | null>(null);
  const [hoveredTopicId, setHoveredTopicId] = useState<number | null>(null);
  const [hoveredArticleId, setHoveredArticleId] = useState<number | null>(null);

  // 加载主题列表
  useEffect(() => {
    fetch("http://localhost:8917/api/topics")
      .then((r) => r.json())
      .then(setTopics)
      .catch(() => {});
  }, [refreshKey]);

  // activeTopicId 变化时自动展开对应主题
  useEffect(() => {
    if (activeTopicId && activeTopicId !== expandedId) {
      setExpandedId(activeTopicId);
      fetch(`http://localhost:8917/api/topics/${activeTopicId}`)
        .then((r) => r.json())
        .then(setTopicDetail)
        .catch(() => {});
    }
  }, [activeTopicId, refreshKey]);

  const handleExpand = async (topicId: number) => {
    if (expandedId === topicId) {
      setExpandedId(null);
      setTopicDetail(null);
      return;
    }
    setExpandedId(topicId);
    const res = await fetch(`http://localhost:8917/api/topics/${topicId}`);
    const data = await res.json();
    setTopicDetail(data);
  };

  const handleDelete = async (topicId: number) => {
    await fetch(`http://localhost:8917/api/topics/${topicId}`, { method: "DELETE" });
    setTopics((prev) => prev.filter((t) => t.id !== topicId));
    if (expandedId === topicId) {
      setExpandedId(null);
      setTopicDetail(null);
    }
  };

  const handleDeleteArticle = async (articleId: number, topicId: number) => {
    await fetch(`http://localhost:8917/api/articles/${articleId}`, { method: "DELETE" });
    if (topicDetail && topicDetail.id === topicId) {
      setTopicDetail({ ...topicDetail, articles: topicDetail.articles.filter((a) => a.id !== articleId) });
    }
    setTopics((prev) => prev.map((t) => t.id === topicId ? { ...t, article_count: t.article_count - 1 } : t));
  };

  const ALL_PLATFORMS: Platform[] = ["wechat", "xiaohongshu", "zhihu"];

  const sectionLabel = (text: string) => (
    <div style={{ fontSize: 12, fontWeight: 600, color: theme.bark, textTransform: "uppercase" as const, letterSpacing: "0.06em", marginBottom: 10 }}>
      {text}
    </div>
  );

  return (
    <div style={{ padding: "28px 24px 24px", display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Brand + New */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: theme.ink, letterSpacing: "-0.03em" }}>
            Content Agent
          </div>
          <div style={{ fontSize: 13, color: theme.bark, marginTop: 3 }}>
            AI 内容生成 Agent
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {onSettings && (
            <Button
              icon={<SettingOutlined />}
              onClick={onSettings}
              size="small"
              style={{ borderRadius: 8, color: theme.bark, borderColor: theme.sand }}
            />
          )}
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onNewTopic}
            size="small"
            style={{ borderRadius: 8, background: theme.amber, borderColor: theme.amber }}
          />
        </div>
      </div>

      {/* Topic List */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {sectionLabel("历史主题")}

        {topics.length === 0 ? (
          <div style={{ fontSize: 13, color: theme.stone, padding: "20px 0", textAlign: "center" }}>
            暂无主题，点击 + 创建
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {topics.map((t) => {
              const isExpanded = expandedId === t.id;
              const isActive = activeTopicId === t.id;
              const isGeneratingHere = isRunning && runningTopicId === t.id;

              return (
                <div key={t.id}>
                  {/* Topic Row */}
                  <div
                    onClick={() => { isGeneratingHere ? onViewRunning() : handleExpand(t.id); }}
                    onMouseEnter={() => setHoveredTopicId(t.id)}
                    onMouseLeave={() => setHoveredTopicId(null)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 12px",
                      borderRadius: 10,
                      cursor: "pointer",
                      background: isActive ? theme.amberSoft : isExpanded ? `${theme.sand}40` : "transparent",
                      border: `1.5px solid ${isActive ? theme.amber : isExpanded ? theme.sand : "transparent"}`,
                      transition: "all 0.2s ease",
                    }}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 14,
                        fontWeight: isActive ? 600 : 400,
                        color: isActive ? theme.amber : theme.ink,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}>
                        {isGeneratingHere && <LoadingOutlined style={{ marginRight: 6, fontSize: 12 }} />}
                        {t.title}
                      </div>
                      <div style={{ fontSize: 11, color: theme.stone, marginTop: 2 }}>
                        {t.article_count} 篇文章
                        {isGeneratingHere && <span style={{ color: theme.amber, marginLeft: 6 }}>生成中...</span>}
                      </div>
                    </div>
                    {!isGeneratingHere && hoveredTopicId === t.id && (
                      <Popconfirm
                        title="删除主题"
                        description="将同时删除该主题下所有文章"
                        onConfirm={() => handleDelete(t.id)}
                        onPopupClick={(e) => e.stopPropagation()}
                        okText="删除"
                        okButtonProps={{ danger: true }}
                        cancelText="取消"
                      >
                        <button
                          onClick={(e) => e.stopPropagation()}
                          style={{
                            background: "none", border: "none", cursor: "pointer",
                            padding: 4, fontSize: 12,
                          }}
                        >
                          <DeleteOutlined style={{ color: theme.error }} />
                        </button>
                      </Popconfirm>
                    )}
                  </div>

                  {/* Expanded: Article List */}
                  {isExpanded && topicDetail && topicDetail.id === t.id && (
                    <div style={{ padding: "8px 12px 12px 24px" }}>
                      {/* 已有文章 */}
                      {topicDetail.articles.map((a) => {
                        const isArticleActive = activeArticleId === a.id;
                        return (
                          <div
                            key={a.id}
                            onClick={() => onSelectArticle(t.id, a)}
                            onMouseEnter={() => setHoveredArticleId(a.id)}
                            onMouseLeave={() => setHoveredArticleId(null)}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                              padding: "8px 10px",
                              borderRadius: 8,
                              cursor: "pointer",
                              marginBottom: 4,
                              background: isArticleActive ? theme.amberSoft : theme.cream,
                              border: `1px solid ${isArticleActive ? theme.amber : "transparent"}`,
                              transition: "all 0.15s",
                            }}
                          >
                            <span
                              style={{
                                fontSize: 11, fontWeight: 600,
                                color: PLATFORM_COLORS[a.platform] || theme.bark,
                                background: `${PLATFORM_COLORS[a.platform] || theme.bark}15`,
                                padding: "2px 8px", borderRadius: 4, flexShrink: 0,
                              }}
                            >
                              {PLATFORM_LABELS[a.platform] || a.platform}
                            </span>
                            <span style={{ fontSize: 12, color: theme.espresso, flex: 1 }}>
                              {a.score > 0 && `${a.score}分`}
                            </span>
                            {a.status === "published" && (
                              <span style={{ fontSize: 10, color: theme.success }}>已发布</span>
                            )}
                            {hoveredArticleId === a.id && (
                              <Popconfirm
                                title="删除文章"
                                description={`确定删除这篇${PLATFORM_LABELS[a.platform] || a.platform}文章吗？`}
                                onConfirm={() => handleDeleteArticle(a.id, t.id)}
                                onPopupClick={(e) => e.stopPropagation()}
                                okText="删除"
                                okButtonProps={{ danger: true }}
                                cancelText="取消"
                              >
                                <button
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    background: "none", border: "none", cursor: "pointer",
                                    padding: 2, fontSize: 11, flexShrink: 0,
                                  }}
                                >
                                  <DeleteOutlined style={{ color: theme.error }} />
                                </button>
                              </Popconfirm>
                            )}
                          </div>
                        );
                      })}

                      {/* 正在生成的平台 — 点击可切回查看进度 */}
                      {isGeneratingHere && runningPlatform && !topicDetail.articles.some(a => a.platform === runningPlatform) && (
                        <div
                          onClick={onViewRunning}
                          style={{
                            display: "flex", alignItems: "center", gap: 8,
                            padding: "8px 10px", borderRadius: 8, marginBottom: 4,
                            background: theme.amberSoft, border: `1px solid ${theme.amber}`,
                            cursor: "pointer",
                          }}
                        >
                          <LoadingOutlined style={{ fontSize: 12, color: theme.amber }} />
                          <span style={{ fontSize: 12, color: theme.amber, fontWeight: 500 }}>
                            正在生成{PLATFORM_LABELS[runningPlatform]}版本...
                          </span>
                        </div>
                      )}

                      {/* 未生成的平台 */}
                      {ALL_PLATFORMS.filter(
                        (p) => !topicDetail.articles.some((a) => a.platform === p) && !(isGeneratingHere && runningPlatform === p)
                      ).map((p) => (
                        <div
                          key={p}
                          onClick={() => !isRunning && onGenerateForPlatform(t.id, t.title, topicDetail.direction, p)}
                          style={{
                            display: "flex", alignItems: "center", gap: 8,
                            padding: "8px 10px", borderRadius: 8, marginBottom: 4,
                            border: `1px dashed ${theme.sand}`,
                            color: isRunning ? theme.sand : theme.stone,
                            fontSize: 12,
                            cursor: isRunning ? "not-allowed" : "pointer",
                            opacity: isRunning ? 0.5 : 1,
                            transition: "all 0.15s",
                          }}
                        >
                          <PlusOutlined style={{ fontSize: 10 }} />
                          生成{PLATFORM_LABELS[p]}版本
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
