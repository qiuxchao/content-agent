"use client";

import { App, Button, Tooltip } from "antd";
import { CopyOutlined, CheckOutlined, SendOutlined } from "@ant-design/icons";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { theme } from "../theme";

const NODE_LABELS: Record<string, string> = {
  planner: "正在拆解关键词",
  researcher: "正在搜索素材",
  writer: "正在写作",
  critic: "正在评估质量",
  increment_retry: "准备重写",
  image_fetcher: "正在获取插图",
  save_memory: "正在保存素材",
};

interface Props {
  article: string;
  isRunning: boolean;
  currentNode: string;
  platform?: string;
  onPublish?: () => void;
}

// 只有公众号支持 API 发布，小红书和知乎只能复制
const PUBLISH_PLATFORMS = ["wechat"];

export function ArticlePanel({ article, isRunning, currentNode, platform, onPublish }: Props) {
  const { message } = App.useApp();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(article);
      setCopied(true);
      message.success("已复制到剪贴板");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      message.error("复制失败");
    }
  };

  // Empty
  if (!article && !isRunning) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", padding: "0 48px" }}>
        <div style={{ textAlign: "center", maxWidth: 360 }}>
          <div
            style={{
              width: 64,
              height: 64,
              borderRadius: 16,
              background: theme.amberSoft,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
              fontSize: 28,
              color: theme.amber,
            }}
          >
            ✦
          </div>
          <div style={{ fontSize: 18, fontWeight: 600, color: theme.espresso, marginBottom: 8 }}>
            准备好了
          </div>
          <div style={{ fontSize: 14, color: theme.bark, lineHeight: 1.7 }}>
            在左侧输入文章主题和目标平台，Agent 会自动搜索素材、撰写初稿、评估质量并配图
          </div>
        </div>
      </div>
    );
  }

  // Loading
  if (!article && isRunning) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ display: "flex", gap: 8, justifyContent: "center", marginBottom: 20 }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  background: theme.amber,
                  animation: "pulse-dot 1.5s ease-in-out infinite",
                  animationDelay: `${i * 0.3}s`,
                }}
              />
            ))}
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, color: theme.espresso, marginBottom: 4 }}>
            {NODE_LABELS[currentNode] || "处理中"}
          </div>
          <div style={{ fontSize: 13, color: theme.bark }}>Agent 正在工作</div>
        </div>
      </div>
    );
  }

  // Article
  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "40px 48px 60px" }}>
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          marginBottom: 24,
          position: "sticky",
          top: 0,
          paddingTop: 12,
          paddingBottom: 12,
          background: `linear-gradient(${theme.cream} 60%, transparent)`,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          <Tooltip title={copied ? "已复制" : "复制全文"}>
            <Button
              icon={copied ? <CheckOutlined /> : <CopyOutlined />}
              onClick={handleCopy}
              size="small"
              style={{
                borderRadius: 8,
                borderColor: copied ? theme.success : theme.sand,
                color: copied ? theme.success : theme.bark,
                background: copied ? theme.successSoft : theme.cream,
              }}
            >
              {copied ? "已复制" : "复制"}
            </Button>
          </Tooltip>
          {onPublish && !isRunning && platform && PUBLISH_PLATFORMS.includes(platform) && (
            <Button
              icon={<SendOutlined />}
              onClick={onPublish}
              size="small"
              style={{
                borderRadius: 8,
                borderColor: theme.amber,
                color: theme.amber,
                background: theme.amberSoft,
              }}
            >
              发布
            </Button>
          )}
        </div>
      </div>

      <div
        className="article-content"
        style={{ animation: "fade-up 0.4s cubic-bezier(0.4,0,0.2,1) forwards" }}
      >
        <ReactMarkdown
          components={{
            a: ({ href, children }) => (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: theme.amber, textDecoration: "underline", textUnderlineOffset: 3 }}
              >
                {children}
              </a>
            ),
          }}
        >
          {article}
        </ReactMarkdown>
      </div>

      {isRunning && (
        <div style={{ marginTop: 32, textAlign: "center", fontSize: 12, color: theme.bark }}>
          <span style={{ display: "inline-block", animation: "pulse-dot 1.5s ease-in-out infinite" }}>●</span>
          {" "}{NODE_LABELS[currentNode] || "处理中"}
        </div>
      )}
    </div>
  );
}
