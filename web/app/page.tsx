"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { InputPanel } from "./components/InputPanel";
import { ArticlePanel } from "./components/ArticlePanel";
import { StatusPanel } from "./components/StatusPanel";
import { PublishPanel } from "./components/PublishPanel";
import { TopicList } from "./components/TopicList";
import { SettingsModal } from "./components/SettingsModal";
import { theme } from "./theme";

export type Platform = "wechat" | "xiaohongshu" | "zhihu";

export interface AgentEvent {
  node: string;
  active?: string;
  data: {
    log?: string[];
    keywords?: string[];
    context?: string;
    draft?: string;
    critic_score?: number;
    critic_feedback?: string;
    final_article?: string;
    retry_count?: number;
    topic_id?: number;
    article_id?: number;
  };
}

type LeftPanel = "topics" | "input";
type RightPanel = "status" | "publish";

export default function Home() {
  // UI 状态
  const [leftPanel, setLeftPanel] = useState<LeftPanel>("topics");
  const [rightPanel, setRightPanel] = useState<RightPanel>("status");

  // 生成状态
  const [isRunning, setIsRunning] = useState(false);
  const [article, setArticle] = useState("");
  const [score, setScore] = useState(0);
  const [currentNode, setCurrentNode] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  // 查看历史文章时，隔离生成状态（ref 给 SSE 回调用，state 给渲染用）
  const [viewingHistory, setViewingHistory] = useState(false);
  const viewingHistoryRef = useRef(false);

  // 始终缓存生成中的最新状态，切回时可恢复
  const genStateRef = useRef({
    article: "",
    score: 0,
    logs: [] as string[],
    keywords: [] as string[],
    currentNode: "",
    topicId: null as number | null,
    articleId: null as number | null,
    platform: "",
  });

  // 数据库关联
  const [currentTopicId, setCurrentTopicId] = useState<number | null>(null);
  const [currentArticleId, setCurrentArticleId] = useState<number | null>(null);
  const [currentPlatform, setCurrentPlatform] = useState<string>("");
  const [runningPlatform, setRunningPlatform] = useState<string>("");
  const [runningTopicId, setRunningTopicId] = useState<number | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [hasTopics, setHasTopics] = useState<boolean | null>(null); // null = loading
  const [settingsOpen, setSettingsOpen] = useState(false);

  const handleGenerate = useCallback(
    async (topic: string, platform: Platform, direction: string, topicId?: number, style?: string) => {
      viewingHistoryRef.current = false;
      setViewingHistory(false);
      genStateRef.current = { article: "", score: 0, logs: [], keywords: [], currentNode: "planner", topicId: topicId ?? null, articleId: null, platform };
      setIsRunning(true);
      setArticle("");
      setScore(0);
      setCurrentNode("planner");
      setLogs([]);
      setKeywords([]);
      setRightPanel("status");
      setLeftPanel("topics");
      setRunningPlatform(platform);
      setRunningTopicId(topicId ?? null);
      setCurrentPlatform(platform);
      if (topicId) setCurrentTopicId(topicId);

      abortRef.current = new AbortController();

      const body: Record<string, unknown> = { topic, platform, direction };
      if (topicId) body.topic_id = topicId;
      if (style) body.style = style;

      try {
        const res = await fetch("http://localhost:8917/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
          signal: abortRef.current.signal,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(errData?.error || `API 错误: ${res.status}`);
        }
        if (!res.body) throw new Error("响应无数据");

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event: AgentEvent = JSON.parse(line.slice(6));

              const gs = genStateRef.current;
              if (event.node === "__done__") {
                // 始终更新 ref 缓存
                gs.article = event.data.final_article || "";
                gs.score = event.data.critic_score || 0;
                if (event.data.log) gs.logs = event.data.log;
                if (event.data.topic_id) gs.topicId = event.data.topic_id;
                if (event.data.article_id) gs.articleId = event.data.article_id;
                gs.currentNode = "";
                // 始终刷新列表，清除 running 标记
                setRefreshKey((k) => k + 1);
                setRunningTopicId(null);
                if (!viewingHistoryRef.current) {
                  setArticle(gs.article);
                  setScore(gs.score);
                  setLogs(gs.logs);
                  if (gs.topicId) setCurrentTopicId(gs.topicId);
                  if (gs.articleId) setCurrentArticleId(gs.articleId);
                  setLeftPanel("topics");
                }
              } else {
                // 始终更新 ref 缓存（active 表示当前正在执行的节点）
                gs.currentNode = event.active || event.node;
                if (event.data.topic_id) {
                  const isNewTopic = gs.topicId !== event.data.topic_id;
                  gs.topicId = event.data.topic_id;
                  setRunningTopicId(event.data.topic_id);
                  if (isNewTopic) {
                    setCurrentTopicId(event.data.topic_id);
                    setRefreshKey((k) => k + 1);
                  }
                }
                if (event.data.log?.length) gs.logs = [...gs.logs, ...event.data.log];
                if (event.data.keywords?.length) gs.keywords = event.data.keywords;
                if (event.data.final_article) gs.article = event.data.final_article;
                if (event.data.critic_score) gs.score = event.data.critic_score;
                if (!viewingHistoryRef.current) {
                  setCurrentNode(gs.currentNode);
                  if (event.data.log?.length) setLogs([...gs.logs]);
                  if (event.data.keywords?.length) setKeywords(gs.keywords);
                  if (event.data.final_article) setArticle(gs.article);
                  if (event.data.critic_score) setScore(gs.score);
                }
              }
            } catch { /* ignore */ }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setLogs((prev) => [...prev, `Error: ${(err as Error).message}`]);
        }
      } finally {
        setIsRunning(false);
        setCurrentNode("");
        setRunningPlatform("");
        setRunningTopicId(null);
      }
    },
    []
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    setCurrentNode("");
  }, []);

  // 文章内容更新（图片上传替换占位符等）
  const handleArticleUpdate = useCallback((newArticle: string) => {
    setArticle(newArticle);
    // 同步更新 genStateRef
    genStateRef.current.article = newArticle;
    // 如果已保存到数据库，同步更新
    if (currentArticleId) {
      fetch(`http://localhost:8917/api/articles/${currentArticleId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content_md: newArticle }),
      }).catch(() => {});
    }
  }, [currentArticleId]);

  // 从历史列表选择已有文章
  const handleSelectArticle = useCallback((topicId: number, articleItem: { id: number; content_md: string; score: number; platform: string }) => {
    viewingHistoryRef.current = true;
    setViewingHistory(true);
    setCurrentTopicId(topicId);
    setCurrentArticleId(articleItem.id);
    setCurrentPlatform(articleItem.platform);
    setArticle(articleItem.content_md);
    setScore(articleItem.score);
    setLogs([]);
    setKeywords([]);
    setRightPanel("status");
  }, []);

  // 切回正在生成的主题：从 ref 恢复显示状态
  const handleViewRunning = useCallback(() => {
    viewingHistoryRef.current = false;
    setViewingHistory(false);
    const gs = genStateRef.current;
    setArticle(gs.article);
    setScore(gs.score);
    setLogs([...gs.logs]);
    setKeywords([...gs.keywords]);
    setCurrentNode(gs.currentNode);
    setCurrentPlatform(gs.platform);
    if (gs.topicId) setCurrentTopicId(gs.topicId);
    if (gs.articleId) setCurrentArticleId(gs.articleId);
    setRightPanel("status");
  }, []);

  // 从历史列表生成新平台版本
  const handleGenerateForPlatform = useCallback(
    (topicId: number, topicTitle: string, direction: string, platform: Platform) => {
      handleGenerate(topicTitle, platform, direction, topicId);
    },
    [handleGenerate]
  );

  // 初始加载：检查是否有历史记录
  useEffect(() => {
    fetch("http://localhost:8917/api/topics")
      .then((r) => r.json())
      .then((data) => {
        const has = Array.isArray(data) && data.length > 0;
        setHasTopics(has);
        if (!has) setLeftPanel("input");
      })
      .catch(() => {
        setHasTopics(false);
        setLeftPanel("input");
      });
  }, []);

  // refreshKey 变化时更新 hasTopics
  useEffect(() => {
    if (refreshKey === 0) return;
    fetch("http://localhost:8917/api/topics")
      .then((r) => r.json())
      .then((data) => setHasTopics(Array.isArray(data) && data.length > 0))
      .catch(() => {});
  }, [refreshKey]);

  // 点新建
  const handleNewTopic = useCallback(() => {
    setLeftPanel("input");
    setArticle("");
    setScore(0);
    setLogs([]);
    setKeywords([]);
    setCurrentTopicId(null);
    setCurrentArticleId(null);
  }, []);

  // 查看历史文章时，不展示生成中的 loading 和右侧面板
  const effectiveRunning = isRunning && !viewingHistory;

  return (
    <div style={{ display: "flex", height: "100vh", background: theme.cream }}>
      {/* Left */}
      <aside
        style={{
          width: 300,
          flexShrink: 0,
          background: theme.creamDeep,
          borderRight: `1px solid ${theme.sand}`,
          overflow: "auto",
        }}
      >
        {leftPanel === "topics" && hasTopics ? (
          <TopicList
            onNewTopic={handleNewTopic}
            onSelectArticle={handleSelectArticle}
            onGenerateForPlatform={handleGenerateForPlatform}
            onViewRunning={handleViewRunning}
            refreshKey={refreshKey}
            activeTopicId={currentTopicId}
            activeArticleId={currentArticleId}
            isRunning={isRunning}
            runningTopicId={runningTopicId}
            runningPlatform={runningPlatform}
            onSettings={() => setSettingsOpen(true)}
          />
        ) : (
          <InputPanel
            onGenerate={(topic, platform, direction, style) => handleGenerate(topic, platform, direction, undefined, style)}
            onStop={handleStop}
            onBack={hasTopics ? () => setLeftPanel("topics") : undefined}
            isRunning={isRunning}
          />
        )}
      </aside>

      {/* Center */}
      <main style={{ flex: 1, overflow: "auto", background: theme.cream }}>
        <ArticlePanel
          article={article}
          isRunning={effectiveRunning}
          currentNode={currentNode}
          platform={currentPlatform}
          onPublish={article && !effectiveRunning ? () => setRightPanel("publish") : undefined}
          onArticleUpdate={handleArticleUpdate}
        />
      </main>

      {/* Right — 只在生成中（非查看历史）/有日志/发布面板时显示 */}
      {(effectiveRunning || logs.length > 0 || rightPanel === "publish") && (
        <aside
          style={{
            width: 320,
            flexShrink: 0,
            background: theme.creamDeep,
            borderLeft: `1px solid ${theme.sand}`,
            overflow: "auto",
          }}
        >
          {rightPanel === "publish" ? (
            <PublishPanel
              article={article}
              onBack={() => setRightPanel("status")}
            />
          ) : (
            <StatusPanel
              currentNode={currentNode}
              keywords={keywords}
              score={score}
              logs={logs}
              isRunning={effectiveRunning}
            />
          )}
        </aside>
      )}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}
