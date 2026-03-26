"use client";

import { useState } from "react";
import { Button, Input } from "antd";
import { theme } from "../theme";
import { WechatIcon, XiaohongshuIcon, ZhihuIcon } from "./PlatformIcons";
import type { Platform } from "../page";

const { TextArea } = Input;

const DIRECTIONS = [
  {
    key: "tech",
    label: "科技 / AI",
    desc: "科技资讯、AI 动态、产品评测",
    role: "你是一位资深科技自媒体作者，擅长把复杂技术用讲故事的方式写清楚。你的文章特点是：信息密度高、有独立观点、读起来不累。你关注 AI、开发工具、互联网产品等方向。",
  },
  {
    key: "finance",
    label: "财经 / 商业",
    desc: "商业分析、投资趋势",
    role: "你是一位财经领域的资深内容创作者，擅长用通俗的语言解读商业逻辑和市场趋势。你的文章特点是：有数据支撑、有独到分析、避免信息茧房。",
  },
  {
    key: "lifestyle",
    label: "生活方式",
    desc: "好物推荐、效率工具",
    role: "你是一位生活方式博主，擅长分享提升生活品质的方法和好物。你的风格是：真实体验为主、有审美品味、不浮夸不做作。",
  },
  {
    key: "education",
    label: "知识 / 教育",
    desc: "学习方法、知识科普",
    role: "你是一位知识分享型创作者，擅长把专业知识讲得通俗有趣。你的文章特点是：逻辑清晰、有实例、让读者有恍然大悟的感觉。",
  },
  {
    key: "custom",
    label: "自定义",
    desc: "自由输入角色描述",
    role: "",
  },
];

const PLATFORMS: { value: Platform; label: string; desc: string; icon: React.ReactNode; brandColor: string }[] = [
  { value: "wechat", label: "公众号", desc: "深度长文", icon: <WechatIcon size={18} />, brandColor: "#07c160" },
  { value: "xiaohongshu", label: "小红书", desc: "种草笔记", icon: <XiaohongshuIcon size={18} />, brandColor: "#fe2c55" },
  { value: "zhihu", label: "知乎", desc: "专业问答", icon: <ZhihuIcon size={18} />, brandColor: "#0066ff" },
];

interface Props {
  onGenerate: (topic: string, platform: Platform, direction: string) => void;
  onStop: () => void;
  onBack?: () => void;
  isRunning: boolean;
}

export function InputPanel({ onGenerate, onStop, onBack, isRunning }: Props) {
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState<Platform>("wechat");
  const [directionKey, setDirectionKey] = useState("tech");
  const [roleText, setRoleText] = useState(DIRECTIONS[0].role);
  const [roleEdited, setRoleEdited] = useState(false);
  const [showRole, setShowRole] = useState(false);

  const handleDirectionChange = (key: string) => {
    setDirectionKey(key);
    const preset = DIRECTIONS.find((d) => d.key === key);
    if (key === "custom") {
      setRoleText("");
      setRoleEdited(true);
      setShowRole(true);
    } else if (preset) {
      setRoleText(preset.role);
      setRoleEdited(false);
    }
  };

  const handleSubmit = () => {
    if (!topic.trim() || isRunning) return;
    // 如果用户编辑过 role，走自定义逻辑；否则走预设 key
    const direction = roleEdited ? roleText.trim() : directionKey;
    onGenerate(topic.trim(), platform, direction || "tech");
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
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 28 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: theme.ink }}>
          新建主题
        </div>
        {onBack && (
          <button
            onClick={onBack}
            style={{ background: "none", border: "none", cursor: "pointer", fontSize: 13, color: theme.bark }}
          >
            ← 返回
          </button>
        )}
      </div>

      {/* Scrollable form area */}
      <div style={{ flex: 1, overflow: "auto", marginBottom: 16 }}>
        {/* Topic */}
        <div style={{ marginBottom: 24 }}>
          {sectionLabel("文章主题")}
          <TextArea
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="例如：2026 年 AI Agent 发展趋势"
            rows={3}
            disabled={isRunning}
            style={{
              background: theme.cream,
              borderColor: theme.sand,
              borderRadius: 10,
              fontSize: 15,
              resize: "none",
              lineHeight: 1.6,
            }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
          />
        </div>

        {/* Direction */}
        <div style={{ marginBottom: 24 }}>
          {sectionLabel("内容方向")}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {DIRECTIONS.map((d) => {
              const isActive = directionKey === d.key;
              return (
                <button
                  key={d.key}
                  type="button"
                  onClick={() => handleDirectionChange(d.key)}
                  disabled={isRunning}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 20,
                    border: `1.5px solid ${isActive ? theme.amber : theme.sand}`,
                    background: isActive ? theme.amberSoft : "transparent",
                    cursor: isRunning ? "not-allowed" : "pointer",
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? theme.amber : theme.espresso,
                    opacity: isRunning ? 0.6 : 1,
                    transition: "all 0.2s ease",
                    whiteSpace: "nowrap",
                  }}
                >
                  {d.label}
                </button>
              );
            })}
          </div>
          {/* 编辑提示词 */}
          <button
            type="button"
            onClick={() => setShowRole(!showRole)}
            disabled={isRunning}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              marginTop: 8,
              padding: 0,
              border: "none",
              background: "none",
              cursor: "pointer",
              fontSize: 12,
              color: theme.stone,
            }}
          >
            <span style={{ transform: showRole ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s", display: "inline-block" }}>▸</span>
            {roleEdited ? "已自定义提示词" : "编辑提示词"}
          </button>
          {showRole && (
            <TextArea
              value={roleText}
              onChange={(e) => {
                setRoleText(e.target.value);
                setRoleEdited(true);
              }}
              placeholder="描述你的写作角色和风格，例如：你是一位美食博主，擅长用生动的文字描述食物的口感和烹饪过程..."
              rows={4}
              disabled={isRunning}
              style={{
                marginTop: 6,
                background: theme.cream,
                borderColor: roleEdited ? theme.amber : theme.sand,
                borderRadius: 10,
                fontSize: 13,
                lineHeight: 1.6,
                resize: "vertical",
              }}
            />
          )}
        </div>

        {/* Platform */}
        <div>
          {sectionLabel("目标平台")}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {PLATFORMS.map((p) => {
              const isActive = platform === p.value;
              return (
                <button
                  key={p.value}
                  type="button"
                  onClick={() => setPlatform(p.value)}
                  disabled={isRunning}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "12px 14px",
                    borderRadius: 10,
                    border: `1.5px solid ${isActive ? theme.amber : theme.sand}`,
                    background: isActive ? theme.amberSoft : "transparent",
                    cursor: isRunning ? "not-allowed" : "pointer",
                    textAlign: "left",
                    opacity: isRunning ? 0.6 : 1,
                    transition: "all 0.2s ease",
                  }}
                >
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      background: isActive ? `${p.brandColor}15` : theme.cream,
                      color: isActive ? p.brandColor : theme.stone,
                      transition: "all 0.2s ease",
                      flexShrink: 0,
                    }}
                  >
                    {p.icon}
                  </span>
                  <span style={{ flex: 1 }}>
                    <span
                      style={{
                        display: "block",
                        fontSize: 15,
                        fontWeight: isActive ? 600 : 500,
                        color: isActive ? theme.ink : theme.espresso,
                        lineHeight: 1.3,
                      }}
                    >
                      {p.label}
                    </span>
                    <span
                      style={{
                        display: "block",
                        fontSize: 12,
                        color: isActive ? theme.bark : theme.stone,
                        marginTop: 1,
                      }}
                    >
                      {p.desc}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Submit */}
      <div>
        {isRunning ? (
          <Button
            onClick={onStop}
            block
            size="large"
            style={{
              borderRadius: 10,
              height: 46,
              fontSize: 15,
              fontWeight: 600,
              background: theme.cream,
              borderColor: theme.error,
              color: theme.error,
            }}
          >
            停止生成
          </Button>
        ) : (
          <Button
            type="primary"
            onClick={handleSubmit}
            disabled={!topic.trim() || (directionKey === "custom" && !roleText.trim())}
            block
            size="large"
            style={{
              borderRadius: 10,
              height: 46,
              fontSize: 15,
              fontWeight: 600,
              ...((topic.trim() && !(directionKey === "custom" && !roleText.trim()))
                ? { background: theme.amber, borderColor: theme.amber }
                : {}),
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 16 }}>✦</span> 开始生成
            </span>
          </Button>
        )}
      </div>
    </div>
  );
}
