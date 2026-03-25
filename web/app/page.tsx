"use client";

import { useState, useRef, useCallback } from "react";
import { InputPanel } from "./components/InputPanel";
import { ArticlePanel } from "./components/ArticlePanel";
import { StatusPanel } from "./components/StatusPanel";
import { theme } from "./theme";

export type Platform = "wechat" | "xiaohongshu" | "zhihu";

export interface AgentEvent {
  node: string;
  data: {
    log?: string[];
    keywords?: string[];
    context?: string;
    draft?: string;
    critic_score?: number;
    critic_feedback?: string;
    final_article?: string;
    retry_count?: number;
  };
}

export default function Home() {
  const [isRunning, setIsRunning] = useState(false);
  const [article, setArticle] = useState("");
  const [score, setScore] = useState(0);
  const [currentNode, setCurrentNode] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [keywords, setKeywords] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const handleGenerate = useCallback(
    async (topic: string, platform: Platform, direction: string) => {
      setIsRunning(true);
      setArticle("");
      setScore(0);
      setCurrentNode("planner");
      setLogs([]);
      setKeywords([]);

      abortRef.current = new AbortController();

      try {
        const res = await fetch("http://localhost:8917/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic, platform, direction }),
          signal: abortRef.current.signal,
        });

        if (!res.ok || !res.body) {
          throw new Error(`API 错误: ${res.status}`);
        }

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
            const jsonStr = line.slice(6);

            try {
              const event: AgentEvent = JSON.parse(jsonStr);

              if (event.node === "__done__") {
                setArticle(event.data.final_article || "");
                setScore(event.data.critic_score || 0);
                if (event.data.log) setLogs(event.data.log);
              } else {
                setCurrentNode(event.node);
                if (event.data.log?.length) {
                  setLogs((prev) => [...prev, ...event.data.log!]);
                }
                if (event.data.keywords?.length) {
                  setKeywords(event.data.keywords);
                }
                if (event.data.final_article) {
                  setArticle(event.data.final_article);
                }
                if (event.data.critic_score) {
                  setScore(event.data.critic_score);
                }
              }
            } catch {
              // ignore
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setLogs((prev) => [...prev, `Error: ${(err as Error).message}`]);
        }
      } finally {
        setIsRunning(false);
        setCurrentNode("");
      }
    },
    []
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    setCurrentNode("");
  }, []);

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
        <InputPanel
          onGenerate={handleGenerate}
          onStop={handleStop}
          isRunning={isRunning}
        />
      </aside>

      {/* Center */}
      <main style={{ flex: 1, overflow: "auto", background: theme.cream }}>
        <ArticlePanel article={article} isRunning={isRunning} currentNode={currentNode} />
      </main>

      {/* Right */}
      <aside
        style={{
          width: 320,
          flexShrink: 0,
          background: theme.creamDeep,
          borderLeft: `1px solid ${theme.sand}`,
          overflow: "auto",
        }}
      >
        <StatusPanel
          currentNode={currentNode}
          keywords={keywords}
          score={score}
          logs={logs}
          isRunning={isRunning}
        />
      </aside>
    </div>
  );
}
