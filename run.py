import time
from agent.graph import run

# ── 修改这两行来切换主题和平台 ──────────────────────────
TOPIC    = "如何开发自己的 AI Agent"
PLATFORM = "xiaohongshu"   # wechat | xiaohongshu | zhihu
# ─────────────────────────────────────────────────────────

print(f"\n🚀 Content Agent 启动")
print(f"   主题：{TOPIC}")
print(f"   平台：{PLATFORM}")

start = time.time()
result = run(TOPIC, PLATFORM)
elapsed = time.time() - start

# 打印运行日志
print(f"\n📋 运行日志（耗时 {elapsed:.1f}s）：")
for line in result["log"]:
    print(f"   {line}")
print(f"\n⭐ 最终评分：{result['score']}/10")

# 打印文章
print("\n" + "─" * 60)
print("📝 生成结果：")
print("─" * 60)
print(result["article"])
print("─" * 60)

# 保存到文件
filename = f"output_{PLATFORM}_{int(time.time())}.md"
with open(filename, "w", encoding="utf-8") as f:
    f.write(result["article"])
print(f"\n✅ 已保存到 {filename}")