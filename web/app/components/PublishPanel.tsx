"use client";

import { useState, useEffect } from "react";
import { Button, Input, Upload, App, Modal } from "antd";
import { UploadOutlined, CheckCircleOutlined, CopyOutlined, EyeOutlined, MobileOutlined, DesktopOutlined } from "@ant-design/icons";
import { theme as t } from "../theme";
import type { UploadFile } from "antd";

const { TextArea } = Input;

interface Props {
  article: string;
  platform?: string;
  onBack: () => void;
}

interface ThemeOption {
  key: string;
  label: string;
}

export function PublishPanel({ article, platform, onBack }: Props) {
  const { message } = App.useApp();
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [themes, setThemes] = useState<ThemeOption[]>([]);
  const [codeThemes, setCodeThemes] = useState<ThemeOption[]>([]);
  const [selectedTheme, setSelectedTheme] = useState("default");
  const [selectedCodeTheme, setSelectedCodeTheme] = useState("atom-one-dark");
  const [serif, setSerif] = useState(true);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [author, setAuthor] = useState("");
  const [cover, setCover] = useState<UploadFile[]>([]);
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(false);
  const [mediaId, setMediaId] = useState("");

  // 预览
  const [previewHtml, setPreviewHtml] = useState("");
  const [showPreview, setShowPreview] = useState(false);
  const [previewMode, setPreviewMode] = useState<"mobile" | "pc">("mobile");
  const [loadingPreview, setLoadingPreview] = useState(false);

  // 封面 prompt
  const [coverPrompt, setCoverPrompt] = useState("");
  const [loadingPrompt, setLoadingPrompt] = useState(false);

  // AI 推荐
  const [recommendReason, setRecommendReason] = useState("");
  const [loadingRecommend, setLoadingRecommend] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8917/api/publish/wechat/status")
      .then((r) => r.json())
      .then((data) => {
        setConfigured(data.configured);
        setThemes(data.themes || []);
        setCodeThemes(data.code_themes || []);
      })
      .catch(() => setConfigured(false));

    if (article) {
      const lines = article.split("\n").filter((l) => l.trim());
      for (const line of lines) {
        if (line.startsWith("# ")) {
          setTitle(line.replace(/^#+\s*/, ""));
          break;
        }
      }
      for (const line of lines) {
        if (!line.startsWith("#") && !line.startsWith("[IMAGE") && !line.startsWith("!")) {
          const clean = line.replace(/[*_`\[\]()]/g, "").trim();
          if (clean.length > 10) {
            setSummary(clean.length > 120 ? clean.slice(0, 117) + "..." : clean);
            break;
          }
        }
      }

    }
  }, [article, platform]);

  // AI 推荐主题（手动触发）
  const handleRecommendTheme = async () => {
    if (!article.trim()) return;
    setLoadingRecommend(true);
    setRecommendReason("");
    try {
      const fd = new FormData();
      fd.append("article", article);
      fd.append("platform", platform || "wechat");
      const res = await fetch("http://localhost:8917/api/publish/wechat/recommend-theme", { method: "POST", body: fd });
      const data = await res.json();
      if (data.theme) setSelectedTheme(data.theme);
      if (data.code_theme) setSelectedCodeTheme(data.code_theme);
      if (data.serif !== undefined) setSerif(data.serif);
      if (data.reason) setRecommendReason(data.reason);
    } catch {
      message.error("推荐失败");
    } finally {
      setLoadingRecommend(false);
    }
  };

  // 获取预览
  const fetchPreview = async (th?: string, ct?: string, sf?: boolean) => {
    const formData = new FormData();
    formData.append("article", article);
    formData.append("theme", th ?? selectedTheme);
    formData.append("code_theme", ct ?? selectedCodeTheme);
    formData.append("serif", String(sf ?? serif));
    const res = await fetch("http://localhost:8917/api/publish/wechat/preview", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    return data.html || "";
  };

  const handlePreview = async () => {
    setLoadingPreview(true);
    try {
      setPreviewHtml(await fetchPreview());
      setShowPreview(true);
    } catch {
      message.error("预览生成失败");
    } finally {
      setLoadingPreview(false);
    }
  };

  // 预览窗口内切换样式 → 实时刷新
  const refreshPreview = async (th: string, ct: string, sf: boolean) => {
    try {
      setPreviewHtml(await fetchPreview(th, ct, sf));
    } catch { /* ignore */ }
  };

  // 生成封面 prompt
  const handleGenCoverPrompt = async () => {
    if (!title.trim()) return;
    setLoadingPrompt(true);
    try {
      const res = await fetch("http://localhost:8917/api/publish/cover-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, summary, direction: "tech" }),
      });
      const data = await res.json();
      setCoverPrompt(data.prompt || "");
    } catch {
      message.error("生成失败");
    } finally {
      setLoadingPrompt(false);
    }
  };

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(coverPrompt);
      message.success("已复制提示词");
    } catch {
      message.error("复制失败");
    }
  };

  const handlePublish = async () => {
    if (!article.trim()) return;
    setPublishing(true);
    const formData = new FormData();
    formData.append("article", article);
    formData.append("theme", selectedTheme);
    formData.append("code_theme", selectedCodeTheme);
    formData.append("serif", String(serif));
    formData.append("title", title);
    formData.append("summary", summary);
    formData.append("author", author);
    if (cover.length > 0 && cover[0].originFileObj) {
      formData.append("cover", cover[0].originFileObj);
    }
    try {
      const res = await fetch("http://localhost:8917/api/publish/wechat", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        setPublished(true);
        setMediaId(data.media_id);
        message.success("已发布到草稿箱");
      } else {
        message.error(data.error || "发布失败");
      }
    } catch {
      message.error("发布请求失败");
    } finally {
      setPublishing(false);
    }
  };

  const sectionLabel = (text: string) => (
    <div style={{ fontSize: 12, fontWeight: 600, color: t.bark, textTransform: "uppercase" as const, letterSpacing: "0.06em", marginBottom: 8 }}>
      {text}
    </div>
  );

  const headerBar = (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
      <span style={{ fontSize: 16, fontWeight: 600, color: t.ink }}>发布到公众号</span>
      <button onClick={onBack} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 13, color: t.bark }}>
        ← 返回
      </button>
    </div>
  );

  // 未配置
  if (configured === false) {
    return (
      <div style={{ padding: "28px 24px" }}>
        {headerBar}
        <div style={{ background: t.amberSoft, borderRadius: 10, padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: t.amber, marginBottom: 8 }}>未配置微信 API</div>
          <div style={{ fontSize: 13, color: t.espresso, lineHeight: 1.7 }}>
            请在 <code style={{ background: t.sand, padding: "1px 6px", borderRadius: 4, fontSize: 12 }}>.env</code> 中添加：
          </div>
          <pre style={{ background: t.cream, borderRadius: 8, padding: 12, marginTop: 10, fontSize: 12, color: t.espresso, overflow: "auto" }}>
{`WECHAT_APP_ID=你的AppID
WECHAT_APP_SECRET=你的AppSecret`}
          </pre>
          <div style={{ fontSize: 12, color: t.bark, marginTop: 10 }}>获取方式：mp.weixin.qq.com → 开发 → 基本配置</div>
        </div>
      </div>
    );
  }

  // 发布成功
  if (published) {
    return (
      <div style={{ padding: "28px 24px" }}>
        {headerBar}
        <div style={{ textAlign: "center", padding: "32px 0" }}>
          <CheckCircleOutlined style={{ fontSize: 48, color: t.success }} />
          <div style={{ fontSize: 16, fontWeight: 600, color: t.ink, marginTop: 16 }}>发布成功</div>
          <div style={{ fontSize: 13, color: t.bark, marginTop: 8, lineHeight: 1.7 }}>
            文章已保存到草稿箱<br />请到{" "}
            <a href="https://mp.weixin.qq.com" target="_blank" rel="noopener noreferrer" style={{ color: t.amber, textDecoration: "underline" }}>
              mp.weixin.qq.com
            </a>
            {" "}查看
          </div>
          {mediaId && <div style={{ fontSize: 11, color: t.stone, marginTop: 12 }}>media_id: {mediaId}</div>}
        </div>
      </div>
    );
  }

  // 预览内切换主题
  const handlePreviewThemeChange = (th: string) => {
    setSelectedTheme(th);
    refreshPreview(th, selectedCodeTheme, serif);
  };
  const handlePreviewCodeThemeChange = (ct: string) => {
    setSelectedCodeTheme(ct);
    refreshPreview(selectedTheme, ct, serif);
  };
  const handlePreviewSerifToggle = () => {
    const next = !serif;
    setSerif(next);
    refreshPreview(selectedTheme, selectedCodeTheme, next);
  };

  const pillBtn = (key: string, active: boolean, label: string, onClick: () => void) => (
    <button
      key={key}
      onClick={onClick}
      style={{
        padding: "3px 10px", borderRadius: 14,
        border: `1px solid ${active ? t.amber : t.sand}`,
        background: active ? t.amberSoft : "transparent",
        cursor: "pointer", fontSize: 11,
        fontWeight: active ? 600 : 400,
        color: active ? t.amber : t.espresso,
        transition: "all 0.15s ease",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );

  // 预览 Modal
  const previewModal = (
    <Modal
      open={showPreview}
      onCancel={() => setShowPreview(false)}
      footer={null}
      width={previewMode === "mobile" ? 480 : 860}
      centered
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span>预览</span>
          <div style={{ display: "flex", gap: 4 }}>
            <button
              onClick={() => setPreviewMode("mobile")}
              style={{
                background: previewMode === "mobile" ? t.amberSoft : "none",
                border: `1px solid ${previewMode === "mobile" ? t.amber : t.sand}`,
                borderRadius: 6, padding: "4px 8px", cursor: "pointer",
                color: previewMode === "mobile" ? t.amber : t.stone, fontSize: 14,
              }}
            >
              <MobileOutlined />
            </button>
            <button
              onClick={() => setPreviewMode("pc")}
              style={{
                background: previewMode === "pc" ? t.amberSoft : "none",
                border: `1px solid ${previewMode === "pc" ? t.amber : t.sand}`,
                borderRadius: 6, padding: "4px 8px", cursor: "pointer",
                color: previewMode === "pc" ? t.amber : t.stone, fontSize: 14,
              }}
            >
              <DesktopOutlined />
            </button>
          </div>
        </div>
      }
    >
      {/* 预览内样式切换栏 */}
      <div style={{ marginBottom: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: t.bark, fontWeight: 600, width: 32 }}>主题</span>
          {themes.map((th) => pillBtn(th.key, selectedTheme === th.key, th.label, () => handlePreviewThemeChange(th.key)))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, color: t.bark, fontWeight: 600, width: 32 }}>代码</span>
          {codeThemes.map((ct) => pillBtn(ct.key, selectedCodeTheme === ct.key, ct.label, () => handlePreviewCodeThemeChange(ct.key)))}
          <span style={{ fontSize: 11, color: t.stone, margin: "0 4px" }}>|</span>
          {pillBtn("serif", serif, "衬线", handlePreviewSerifToggle)}
          {pillBtn("sans", !serif, "无衬线", handlePreviewSerifToggle)}
        </div>
      </div>

      <div style={{
        maxHeight: "65vh", overflow: "auto",
        borderRadius: 10, border: `1px solid ${t.sand}`, background: "#fff",
        width: previewMode === "mobile" ? 375 : "100%",
        margin: "0 auto",
        padding: previewMode === "mobile" ? "20px 16px" : "24px 20px",
        fontSize: previewMode === "mobile" ? 15 : 16,
        transition: "all 0.3s ease",
      }}>
        <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
      </div>
    </Modal>
  );

  // 主界面
  return (
    <div style={{ padding: "28px 24px 24px", display: "flex", flexDirection: "column", height: "100%" }}>
      {previewModal}
      {headerBar}

      <div style={{ flex: 1, overflow: "auto" }}>
        {/* 主题选择 */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            {sectionLabel("文章主题风格")}
            <div style={{ display: "flex", gap: 6 }}>
              <Button
                size="small"
                loading={loadingRecommend}
                onClick={handleRecommendTheme}
                disabled={!article.trim()}
                style={{ borderRadius: 6, fontSize: 12, borderColor: t.sand, color: t.bark }}
              >
                AI 推荐
              </Button>
              <Button
                icon={<EyeOutlined />}
                size="small"
                loading={loadingPreview}
                onClick={handlePreview}
                style={{ borderRadius: 6, fontSize: 12, borderColor: t.sand, color: t.bark }}
              >
                预览
              </Button>
            </div>
          </div>
          {recommendReason && (
            <div style={{ fontSize: 12, color: t.bark, marginBottom: 8, padding: "4px 8px", background: t.amberSoft, borderRadius: 6 }}>
              AI 推荐：{recommendReason}
            </div>
          )}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {themes.map((th) => {
              const isActive = selectedTheme === th.key;
              return (
                <button
                  key={th.key}
                  onClick={() => setSelectedTheme(th.key)}
                  style={{
                    padding: "5px 12px", borderRadius: 20,
                    border: `1.5px solid ${isActive ? t.amber : t.sand}`,
                    background: isActive ? t.amberSoft : "transparent",
                    cursor: "pointer", fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? t.amber : t.espresso,
                    transition: "all 0.2s ease",
                  }}
                >
                  {th.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 衬线字体开关 */}
        <div style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {sectionLabel("衬线字体")}
          <button
            onClick={() => setSerif(!serif)}
            style={{
              position: "relative",
              width: 40, height: 22, borderRadius: 11,
              border: "none", cursor: "pointer",
              background: serif ? t.amber : t.sand,
              transition: "background 0.2s ease",
            }}
          >
            <span style={{
              position: "absolute",
              top: 3, left: serif ? 21 : 3,
              width: 16, height: 16, borderRadius: "50%",
              background: "#fff",
              transition: "left 0.2s ease",
              boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
            }} />
          </button>
        </div>

        {/* 代码主题选择 */}
        <div style={{ marginBottom: 16 }}>
          {sectionLabel("代码高亮风格")}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {codeThemes.map((ct) => {
              const isActive = selectedCodeTheme === ct.key;
              return (
                <button
                  key={ct.key}
                  onClick={() => setSelectedCodeTheme(ct.key)}
                  style={{
                    padding: "5px 12px", borderRadius: 20,
                    border: `1.5px solid ${isActive ? t.amber : t.sand}`,
                    background: isActive ? t.amberSoft : "transparent",
                    cursor: "pointer", fontSize: 12,
                    fontWeight: isActive ? 600 : 400,
                    color: isActive ? t.amber : t.espresso,
                    transition: "all 0.2s ease",
                  }}
                >
                  {ct.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* 标题 */}
        <div style={{ marginBottom: 14 }}>
          {sectionLabel("标题")}
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="文章标题"
            style={{ borderRadius: 10, borderColor: t.sand, background: t.cream, fontSize: 14 }}
          />
        </div>

        {/* 摘要 */}
        <div style={{ marginBottom: 14 }}>
          {sectionLabel("摘要")}
          <TextArea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="文章摘要"
            rows={2}
            style={{ borderRadius: 10, borderColor: t.sand, background: t.cream, fontSize: 13, resize: "none" }}
          />
        </div>

        {/* 作者 */}
        <div style={{ marginBottom: 14 }}>
          {sectionLabel("作者")}
          <Input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="留空则使用 .env 中的默认作者"
            style={{ borderRadius: 10, borderColor: t.sand, background: t.cream, fontSize: 14 }}
          />
        </div>

        {/* 封面图 */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            {sectionLabel("封面图")}
          </div>
          <Upload
            fileList={cover}
            onChange={({ fileList }) => setCover(fileList.slice(-1))}
            beforeUpload={() => false}
            accept="image/*"
            maxCount={1}
          >
            <Button icon={<UploadOutlined />} size="small" style={{ borderRadius: 8, borderColor: t.sand }}>
              选择图片
            </Button>
          </Upload>

          {/* 封面 prompt 生成 */}
          <div style={{ marginTop: 10, padding: 10, background: t.cream, borderRadius: 8, border: `1px solid ${t.sand}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: t.bark }}>✦ AI 封面提示词</span>
              <Button
                size="small"
                loading={loadingPrompt}
                onClick={handleGenCoverPrompt}
                disabled={!title.trim()}
                style={{ borderRadius: 6, fontSize: 11, height: 24, borderColor: t.sand, color: t.bark }}
              >
                生成
              </Button>
            </div>
            {coverPrompt ? (
              <div>
                <div style={{ fontSize: 12, color: t.espresso, lineHeight: 1.6, marginBottom: 6, wordBreak: "break-all" }}>
                  {coverPrompt}
                </div>
                <Button
                  icon={<CopyOutlined />}
                  size="small"
                  onClick={handleCopyPrompt}
                  style={{ borderRadius: 6, fontSize: 11, height: 24, borderColor: t.sand, color: t.bark }}
                >
                  复制
                </Button>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: t.stone }}>
                点击生成，复制到 ChatGPT / Gemini / 即梦等平台生成封面
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 发布按钮 */}
      <Button
        type="primary"
        onClick={handlePublish}
        loading={publishing}
        disabled={!title.trim() || configured === null}
        block
        size="large"
        style={{
          borderRadius: 10, height: 46, fontSize: 15, fontWeight: 600,
          ...(title.trim() ? { background: t.amber, borderColor: t.amber } : {}),
        }}
      >
        {publishing ? "发布中..." : "发布到草稿箱"}
      </Button>
    </div>
  );
}
