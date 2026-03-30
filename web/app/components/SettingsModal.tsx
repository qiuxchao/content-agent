"use client";

import { useEffect, useState } from "react";
import { App, Modal, Input, Select, Button, Spin, Tooltip, Switch } from "antd";
import { QuestionCircleOutlined } from "@ant-design/icons";
import { theme } from "../theme";

interface Props {
  open: boolean;
  onClose: () => void;
}

// ── 选项数据 ────────────────────────────────────────────

const LLM_PROVIDERS = [
  { value: "openai", label: "OpenAI 兼容（含 DeepSeek、Kimi、通义等）" },
  { value: "anthropic", label: "Anthropic 兼容" },
];

const IMAGE_PROVIDERS = [
  { value: "prompt", label: "仅生成提示词（免费，手动生图后上传）" },
  { value: "screenshot", label: "网页截图（Playwright，截取官方页面）" },
  { value: "mixed", label: "混合模式（截图 + AI 生图，自动选择）" },
  { value: "unsplash", label: "Unsplash 图片搜索（免费）" },
  { value: "openai", label: "OpenAI 兼容（含 Seedream/豆包 等）" },
  { value: "gemini", label: "Google Gemini" },
  { value: "openrouter", label: "OpenRouter（聚合多模型）" },
  { value: "replicate", label: "Replicate（托管模型，按量付费）" },
  { value: "dashscope", label: "通义万相" },
];

const IMAGE_STYLES = [
  { value: "", label: "自动（按平台推荐）" },
  { value: "warm", label: "🌅 温暖 — 柔和水彩，暖橙奶油色" },
  { value: "fresh", label: "🌿 新鲜 — 清新扁平，薄荷天蓝色" },
  { value: "minimal", label: "◻️ 极简 — 大量留白，单色线条" },
  { value: "notion", label: "📝 概念 — Notion 风格，黑白线稿" },
  { value: "retro", label: "📻 复古 — 70s 质感，锈色橄榄色" },
  { value: "bold", label: "🔥 粗体 — 高对比，红黄黑撞色" },
  { value: "cute", label: "🎀 可爱 — 粉紫马卡龙色，圆润形状" },
  { value: "chalkboard", label: "🖍️ 黑板 — 粉笔手绘，深色背景" },
];

// ── 提示文案 ────────────────────────────────────────────

const TIPS: Record<string, { label: string; tip: string; placeholder?: string }> = {
  // LLM
  LLM_PROVIDER: {
    label: "模型服务商",
    tip: "选 OpenAI 兼容可接入 DeepSeek、Kimi、通义、硅基流动等，只需改 Base URL 和模型名",
  },
  LLM_API_KEY: {
    label: "API 密钥",
    tip: "在服务商控制台获取。如 OpenAI: platform.openai.com/api-keys，DeepSeek: platform.deepseek.com/api-keys",
    placeholder: "sk-...",
  },
  LLM_BASE_URL: {
    label: "API 地址",
    tip: "OpenAI 官方可留空。其他服务商填写对应地址，例如：\n• DeepSeek: https://api.deepseek.com\n• Kimi: https://api.moonshot.cn/v1\n• 通义: https://dashscope.aliyuncs.com/compatible-mode/v1\n• 硅基流动: https://api.siliconflow.cn/v1",
    placeholder: "留空使用 OpenAI 官方地址",
  },
  LLM_MODEL: {
    label: "模型名称",
    tip: "推荐：gpt-5.4-mini（OpenAI）、deepseek-chat（DeepSeek）、kimi-k2.5（Kimi）、qwen-max-latest（通义）、claude-sonnet-4-6（Anthropic）",
    placeholder: "例如 gpt-5.4-mini 或 deepseek-chat",
  },
  // Search
  TAVILY_API_KEY: {
    label: "Tavily 搜索密钥",
    tip: "用于文章写作时的实时搜索。免费额度 1000 次/月。\n获取地址: app.tavily.com（注册即可）",
    placeholder: "tvly-...",
  },
  // Image - Unsplash
  UNSPLASH_ACCESS_KEY: {
    label: "Unsplash 密钥",
    tip: "免费图片搜索服务，获取地址: unsplash.com/developers\n注册后创建 App 即可获得 Access Key",
    placeholder: "Unsplash Access Key",
  },
  // Image - 统一字段
  IMAGE_API_KEY: {
    label: "API 密钥",
    tip: "留空则复用上方大语言模型的 API 密钥",
    placeholder: "留空则复用 LLM API Key",
  },
  IMAGE_BASE_URL: {
    label: "API 地址",
    tip: "留空使用服务商默认地址。自定义示例：\n• Seedream/豆包: https://ark.cn-beijing.volces.com/api/v3",
    placeholder: "留空使用默认地址",
  },
  IMAGE_MODEL: {
    label: "生图模型",
    tip: "留空使用默认。推荐：\n• OpenAI: gpt-image-1\n• Seedream: doubao-seedream-5-0-260128\n• Gemini: gemini-2.0-flash-preview-image-generation\n• OpenRouter: google/gemini-2.0-flash-preview-image-generation\n• Replicate: google/nano-banana-pro\n• 通义: qwen-image-2.0-pro",
    placeholder: "留空使用默认模型",
  },
  IMAGE_STYLE: {
    label: "默认配图风格",
    tip: "自动模式下：公众号用温暖风格、小红书用新鲜风格、知乎用极简风格。也可以在生成时单独选择",
  },
  IMAGE_CONCURRENT: {
    label: "并发生图",
    tip: "多张配图时是否同时请求。多数生图模型不支持并发，开启可能导致限流报错。Unsplash 搜图不受此限制",
  },
  // WeChat
  WECHAT_APP_ID: {
    label: "公众号 App ID",
    tip: "用于一键发布到微信公众号草稿箱。\n获取方式: mp.weixin.qq.com → 设置与开发 → 基本配置",
    placeholder: "wx...",
  },
  WECHAT_APP_SECRET: {
    label: "公众号 App Secret",
    tip: "与 App ID 配对使用，同一位置获取",
    placeholder: "App Secret",
  },
};

// Provider 默认 Base URL 占位提示
const IMAGE_BASE_PLACEHOLDERS: Record<string, string> = {
  openai: "留空使用 api.openai.com（Seedream 填 ark 地址）",
  gemini: "留空使用 generativelanguage.googleapis.com",
  openrouter: "留空使用 openrouter.ai",
  replicate: "留空使用 api.replicate.com",
  dashscope: "留空使用 dashscope.aliyuncs.com",
};

// ── 组件 ────────────────────────────────────────────────

export function SettingsModal({ open, onClose }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const { message } = App.useApp();

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    fetch("http://localhost:8917/api/settings")
      .then((r) => r.json())
      .then((data) => setValues(data?.settings || {}))
      .catch(() => message.error("加载设置失败"))
      .finally(() => setLoading(false));
  }, [open, message]);

  const update = (key: string, val: string) => {
    setValues((prev) => ({ ...prev, [key]: val }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch("http://localhost:8917/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ settings: values }),
      });
      if (!res.ok) throw new Error("Save failed");
      message.success("设置已保存，部分配置需重启后端生效");
      onClose();
    } catch {
      message.error("保存失败，请重试");
    } finally {
      setSaving(false);
    }
  };

  const imageProvider = values.IMAGE_PROVIDER || "unsplash";

  // ── 渲染辅助 ──────────────────────────────────────────

  const sectionHeader = (title: string, desc?: string, first?: boolean) => (
    <div style={{ marginTop: first ? 0 : 12 }}>
      <div style={{
        fontSize: 14, fontWeight: 700, color: theme.ink,
        paddingBottom: 8, borderBottom: `1.5px solid ${theme.sand}`,
      }}>
        {title}
      </div>
      {desc && (
        <div style={{ fontSize: 12, color: theme.stone, marginTop: 6, lineHeight: 1.6 }}>
          {desc}
        </div>
      )}
    </div>
  );

  const field = (key: string, content: React.ReactNode) => {
    const info = TIPS[key];
    if (!info) return content;
    return (
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 8 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: theme.espresso }}>{info.label}</span>
          <Tooltip
            title={<span style={{ whiteSpace: "pre-line", fontSize: 12 }}>{info.tip}</span>}
            placement="topLeft"
            styles={{ root: { maxWidth: 360 } }}
          >
            <QuestionCircleOutlined style={{ fontSize: 12, color: theme.stone, cursor: "help" }} />
          </Tooltip>
        </div>
        {content}
      </div>
    );
  };

  const inputStyle: React.CSSProperties = {
    background: theme.cream,
    borderColor: theme.sand,
    borderRadius: 8,
    fontSize: 13,
  };

  return (
    <Modal
      title={<span style={{ color: theme.ink, fontWeight: 700, fontSize: 17 }}>设置</span>}
      open={open}
      onCancel={onClose}
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "4px 0" }}>
          <Button onClick={onClose} style={{ borderRadius: 8 }}>取消</Button>
          <Button
            type="primary"
            onClick={handleSave}
            loading={saving}
            style={{ borderRadius: 8, background: theme.amber, borderColor: theme.amber }}
          >
            保存
          </Button>
        </div>
      }
      width={540}
      styles={{
        body: { maxHeight: "65vh", overflow: "auto", padding: "4px 8px 16px" },
      }}
    >
      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 48 }}><Spin /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* ── 大语言模型 ── */}
          {sectionHeader("大语言模型", "用于文章撰写、质量评估等 AI 能力", true)}

          {field("LLM_PROVIDER",
            <Select
              value={values.LLM_PROVIDER || "openai"}
              onChange={(v) => update("LLM_PROVIDER", v)}
              options={LLM_PROVIDERS}
              style={{ width: "100%", ...inputStyle }}
            />
          )}

          {field("LLM_API_KEY",
            <Input.Password
              value={values.LLM_API_KEY || ""}
              onChange={(e) => update("LLM_API_KEY", e.target.value)}
              placeholder={TIPS.LLM_API_KEY.placeholder}
              style={inputStyle}
            />
          )}

          {field("LLM_BASE_URL",
            <Input
              value={values.LLM_BASE_URL || ""}
              onChange={(e) => update("LLM_BASE_URL", e.target.value)}
              placeholder={TIPS.LLM_BASE_URL.placeholder}
              style={inputStyle}
            />
          )}

          {field("LLM_MODEL",
            <Input
              value={values.LLM_MODEL || ""}
              onChange={(e) => update("LLM_MODEL", e.target.value)}
              placeholder={TIPS.LLM_MODEL.placeholder}
              style={inputStyle}
            />
          )}

          {/* ── 搜索 ── */}
          {sectionHeader("网络搜索", "文章写作时搜索实时资料，避免 AI 编造内容")}

          {field("TAVILY_API_KEY",
            <Input.Password
              value={values.TAVILY_API_KEY || ""}
              onChange={(e) => update("TAVILY_API_KEY", e.target.value)}
              placeholder={TIPS.TAVILY_API_KEY.placeholder}
              style={inputStyle}
            />
          )}

          {/* ── 配图 ── */}
          {sectionHeader("文章配图", "为文章自动生成或搜索配图")}

          {field("IMAGE_PROVIDER",
            <Select
              value={imageProvider}
              onChange={(v) => update("IMAGE_PROVIDER", v)}
              options={IMAGE_PROVIDERS}
              style={{ width: "100%" }}
            />
          )}

          {imageProvider === "screenshot" && (
            <div style={{ fontSize: 12, color: theme.stone, marginTop: 4, lineHeight: 1.6 }}>
              需要安装 Playwright：uv pip install playwright && python -m playwright install chromium
            </div>
          )}

          {imageProvider === "unsplash" && field("UNSPLASH_ACCESS_KEY",
            <Input.Password
              value={values.UNSPLASH_ACCESS_KEY || ""}
              onChange={(e) => update("UNSPLASH_ACCESS_KEY", e.target.value)}
              placeholder={TIPS.UNSPLASH_ACCESS_KEY.placeholder}
              style={inputStyle}
            />
          )}

          {imageProvider !== "unsplash" && imageProvider !== "prompt" && imageProvider !== "screenshot" && (
            <>
              {field("IMAGE_API_KEY",
                <Input.Password
                  value={values.IMAGE_API_KEY || ""}
                  onChange={(e) => update("IMAGE_API_KEY", e.target.value)}
                  placeholder={TIPS.IMAGE_API_KEY.placeholder}
                  style={inputStyle}
                />
              )}

              {field("IMAGE_BASE_URL",
                <Input
                  value={values.IMAGE_BASE_URL || ""}
                  onChange={(e) => update("IMAGE_BASE_URL", e.target.value)}
                  placeholder={IMAGE_BASE_PLACEHOLDERS[imageProvider] || "留空使用默认地址"}
                  style={inputStyle}
                />
              )}

              {field("IMAGE_MODEL",
                <Input
                  value={values.IMAGE_MODEL || ""}
                  onChange={(e) => update("IMAGE_MODEL", e.target.value)}
                  placeholder={TIPS.IMAGE_MODEL.placeholder}
                  style={inputStyle}
                />
              )}
            </>
          )}

          {field("IMAGE_STYLE",
            <Select
              value={values.IMAGE_STYLE || ""}
              onChange={(v) => update("IMAGE_STYLE", v)}
              options={IMAGE_STYLES}
              style={{ width: "100%", ...inputStyle }}
            />
          )}

          {imageProvider !== "unsplash" && imageProvider !== "prompt" && field("IMAGE_CONCURRENT",
            <Switch
              checked={values.IMAGE_CONCURRENT === "true"}
              onChange={(v) => update("IMAGE_CONCURRENT", v ? "true" : "false")}
              size="small"
            />
          )}

          {/* ── 微信公众号 ── */}
          {sectionHeader("微信公众号", "配置后可一键发布文章到公众号草稿箱（可选）")}

          {field("WECHAT_APP_ID",
            <Input
              value={values.WECHAT_APP_ID || ""}
              onChange={(e) => update("WECHAT_APP_ID", e.target.value)}
              placeholder={TIPS.WECHAT_APP_ID.placeholder}
              style={inputStyle}
            />
          )}

          {field("WECHAT_APP_SECRET",
            <Input.Password
              value={values.WECHAT_APP_SECRET || ""}
              onChange={(e) => update("WECHAT_APP_SECRET", e.target.value)}
              placeholder={TIPS.WECHAT_APP_SECRET.placeholder}
              style={inputStyle}
            />
          )}
        </div>
      )}
    </Modal>
  );
}
