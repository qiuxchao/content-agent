"use client";

import { App, Button, Tooltip, Upload } from "antd";
import { CopyOutlined, CheckOutlined, SendOutlined, UploadOutlined, PictureOutlined } from "@ant-design/icons";
import { useState, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
  onArticleUpdate?: (newArticle: string) => void;
}

// 只有公众号支持 API 发布，小红书和知乎只能复制
const PUBLISH_PLATFORMS = ["wechat"];

export function ArticlePanel({ article, isRunning, currentNode, platform, onPublish, onArticleUpdate }: Props) {
  const { message } = App.useApp();
  const [copied, setCopied] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState<string | null>(null);
  const [uploadingPrompt, setUploadingPrompt] = useState<string | null>(null);

  const handleCopyPrompt = useCallback(async (prompt: string) => {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedPrompt(prompt);
      message.success("提示词已复制，可粘贴到 Gemini 等平台生图");
      setTimeout(() => setCopiedPrompt(null), 2000);
    } catch {
      message.error("复制失败");
    }
  }, [message]);

  const handleUploadImage = useCallback(async (prompt: string, file: File) => {
    setUploadingPrompt(prompt);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("http://localhost:8917/api/upload-image", { method: "POST", body: form });
      if (!res.ok) throw new Error("上传失败");
      const { url } = await res.json();
      // 替换占位符为真实图片
      const placeholder = `![${prompt}](prompt-placeholder)`;
      const replacement = `![illustration](${url})`;
      const newArticle = article.replace(placeholder, replacement);
      onArticleUpdate?.(newArticle);
      message.success("图片已上传");
    } catch {
      message.error("上传失败，请重试");
    } finally {
      setUploadingPrompt(null);
    }
  }, [article, onArticleUpdate, message]);

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
          remarkPlugins={[remarkGfm]}
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
            // 含图片占位符的段落用 div 替代 p，避免 <div> 嵌套在 <p> 内的 hydration 错误
            p: ({ children, node }) => {
              const hasBlockChild = node?.children?.some(
                (child: { type: string; tagName?: string }) =>
                  child.type === "element" && child.tagName === "img"
              );
              return hasBlockChild
                ? <div style={{ marginBottom: "1em" }}>{children}</div>
                : <p>{children}</p>;
            },
            img: ({ src, alt }) => {
              if (src === "prompt-placeholder" && alt) {
                const prompt = alt;
                const isCopied = copiedPrompt === prompt;
                const isUploading = uploadingPrompt === prompt;
                return (
                  <div
                    style={{
                      margin: "16px 0",
                      padding: "16px 20px",
                      borderRadius: 12,
                      border: `1.5px dashed ${theme.sand}`,
                      background: theme.creamDeep,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                      <PictureOutlined style={{ fontSize: 16, color: theme.amber }} />
                      <span style={{ fontSize: 13, fontWeight: 600, color: theme.espresso }}>
                        配图占位 — 可手动上传
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: theme.bark,
                        lineHeight: 1.6,
                        background: theme.cream,
                        padding: "8px 12px",
                        borderRadius: 8,
                        marginBottom: 12,
                        maxHeight: 80,
                        overflow: "auto",
                        wordBreak: "break-word",
                      }}
                    >
                      {prompt}
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <Button
                        size="small"
                        icon={isCopied ? <CheckOutlined /> : <CopyOutlined />}
                        onClick={() => handleCopyPrompt(prompt)}
                        style={{
                          borderRadius: 6,
                          fontSize: 12,
                          borderColor: isCopied ? theme.success : theme.sand,
                          color: isCopied ? theme.success : theme.bark,
                        }}
                      >
                        {isCopied ? "已复制" : "复制提示词"}
                      </Button>
                      <Upload
                        accept="image/*"
                        showUploadList={false}
                        beforeUpload={(file) => {
                          handleUploadImage(prompt, file);
                          return false;
                        }}
                      >
                        <Button
                          size="small"
                          icon={<UploadOutlined />}
                          loading={isUploading}
                          style={{
                            borderRadius: 6,
                            fontSize: 12,
                            borderColor: theme.amber,
                            color: theme.amber,
                          }}
                        >
                          上传图片
                        </Button>
                      </Upload>
                    </div>
                  </div>
                );
              }
              // 普通图片
              return <img src={src} alt={alt} style={{ maxWidth: "100%", borderRadius: 8 }} />;
            },
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
