"use client";

import { useEffect, useRef } from "react";
import { Tag, Progress } from "antd";
import { theme } from "../theme";

const PIPELINE = [
  { key: "pre_researcher", label: "预搜索" },
  { key: "planner", label: "分析选题" },
  { key: "researcher", label: "补充搜索" },
  { key: "writer", label: "写作" },
  { key: "critic", label: "质量评估" },
  { key: "image_fetcher", label: "获取插图" },
  { key: "save_memory", label: "保存素材" },
];

interface Props {
  currentNode: string;
  keywords: string[];
  score: number;
  logs: string[];
  isRunning: boolean;
}

export function StatusPanel({ currentNode, keywords, score, logs, isRunning }: Props) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const hasError = !isRunning && logs.length > 0 && logs[logs.length - 1]?.startsWith("Error");

  const getNodeStatus = (nodeKey: string) => {
    if (!isRunning && !logs.length) return "idle";
    const nodeIndex = PIPELINE.findIndex((n) => n.key === nodeKey);
    const currentIndex = PIPELINE.findIndex((n) => n.key === currentNode);

    if (isRunning) {
      if (currentNode === nodeKey) return "active";
      if (currentIndex > nodeIndex) return "done";
      return "idle";
    }

    if (hasError) {
      if (nodeIndex < currentIndex) return "done";
      if (nodeIndex === currentIndex) return "error";
      return "idle";
    }

    return "done";
  };

  const getScoreColor = () => {
    if (score >= 8) return theme.success;
    if (score >= 7) return theme.amber;
    if (score >= 5) return "#d4a017";
    return theme.error;
  };

  const sectionLabel = (text: string) => (
    <div
      style={{
        fontSize: 12,
        fontWeight: 600,
        color: theme.bark,
        textTransform: "uppercase" as const,
        letterSpacing: "0.06em",
        marginBottom: 10,
      }}
    >
      {text}
    </div>
  );

  return (
    <div style={{ padding: "28px 24px 24px", display: "flex", flexDirection: "column", height: "100%" }}>
      {sectionLabel("Agent 流水线")}

      {/* Pipeline */}
      <div style={{ marginBottom: 24 }}>
        {PIPELINE.map((node, i) => {
          const status = getNodeStatus(node.key);
          const isLast = i === PIPELINE.length - 1;
          const dotColor =
            status === "done" ? theme.success
            : status === "active" ? theme.amber
            : status === "error" ? theme.error
            : theme.sand;

          return (
            <div key={node.key} style={{ display: "flex", gap: 12 }}>
              {/* Dot + Line */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 20 }}>
                <div
                  style={{
                    width: status === "active" ? 12 : 8,
                    height: status === "active" ? 12 : 8,
                    borderRadius: "50%",
                    background: dotColor,
                    transition: "all 0.3s ease",
                    flexShrink: 0,
                    marginTop: status === "active" ? 4 : 6,
                    ...(status === "active" ? { animation: "pulse-dot 1.5s ease-in-out infinite" } : {}),
                  }}
                />
                {!isLast && (
                  <div
                    style={{
                      width: 1.5,
                      flex: 1,
                      minHeight: 16,
                      background: status === "done" ? theme.success : theme.sand,
                      transition: "background 0.3s ease",
                    }}
                  />
                )}
              </div>

              {/* Label */}
              <div
                style={{
                  fontSize: 14,
                  fontWeight: status === "active" ? 600 : 400,
                  color:
                    status === "done" ? theme.success
                    : status === "active" ? theme.amber
                    : status === "error" ? theme.error
                    : theme.stone,
                  paddingBottom: isLast ? 0 : 12,
                  transition: "all 0.3s ease",
                }}
              >
                {node.label}
                {status === "active" && (
                  <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.7 }}>...</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Keywords */}
      {keywords.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          {sectionLabel("搜索关键词")}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {keywords.map((kw, i) => (
              <Tag
                key={i}
                style={{
                  margin: 0,
                  background: theme.amberSoft,
                  borderColor: theme.amberGlow,
                  color: theme.amber,
                  fontSize: 12,
                  borderRadius: 6,
                  padding: "2px 10px",
                }}
              >
                {kw}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {/* Score */}
      {score > 0 && (
        <div style={{ marginBottom: 24 }}>
          {sectionLabel("质量评分")}
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Progress
              percent={score * 10}
              strokeColor={getScoreColor()}
              railColor={theme.sand}
              showInfo={false}
              size="small"
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 18, fontWeight: 700, color: getScoreColor(), fontVariantNumeric: "tabular-nums" }}>
              {score}
              <span style={{ fontSize: 12, fontWeight: 400, color: theme.stone }}>/10</span>
            </span>
          </div>
        </div>
      )}

      {/* Logs */}
      <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        {sectionLabel("运行日志")}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            background: theme.cream,
            borderRadius: 10,
            padding: "12px 14px",
            border: `1px solid ${theme.sand}`,
          }}
        >
          {logs.length === 0 ? (
            <div style={{ fontSize: 13, color: theme.stone }}>等待开始...</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {logs.map((line, i) => (
                <div
                  key={i}
                  style={{
                    fontSize: 13,
                    lineHeight: 1.7,
                    color: line.startsWith("Error") ? theme.error : theme.espresso,
                  }}
                >
                  {line}
                </div>
              ))}
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
