"""查看向量库中存储的所有素材"""
from dotenv import load_dotenv
load_dotenv()

import chromadb

client = chromadb.PersistentClient(path="data/vectorstore")
collection = client.get_collection("content_agent_materials")

# 获取所有记录
results = collection.get(include=["documents", "metadatas"])

print(f"📚 向量库共有 {collection.count()} 条素材\n")

for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
    print(f"{'─' * 50}")
    print(f"#{i+1}  主题：{meta.get('topic', '未知')}")
    print(f"    平台：{meta.get('platform', '未知')}")
    print(f"    时间：{meta.get('timestamp', '未知')}")
    print(f"    内容：{doc[:200]}...")
    print()
