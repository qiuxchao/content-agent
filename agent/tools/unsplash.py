import os
import requests
from dataclasses import dataclass


@dataclass
class UnsplashImage:
    url: str        # regular 尺寸，直接用于展示
    alt: str        # 图片描述
    credit: str     # 摄影师署名，展示时必须带上（Unsplash 要求）


def search_images(keyword: str, count: int = 1) -> list[UnsplashImage]:
    """
    根据英文关键词搜索 Unsplash 图片。
    keyword 建议用英文，搜索质量更好。
    """
    resp = requests.get(
        "https://api.unsplash.com/search/photos",
        params={
            "query": keyword,
            "per_page": count,
            "orientation": "landscape",
        },
        headers={
            "Authorization": f"Client-ID {os.getenv('UNSPLASH_ACCESS_KEY')}"
        },
        timeout=10,
    )

    if resp.status_code != 200:
        print(f"  [Unsplash] 请求失败 ({resp.status_code}): {keyword}")
        return []

    results = resp.json().get("results", [])
    if not results:
        print(f"  [Unsplash] 未找到图片: {keyword}")
        return []

    return [
        UnsplashImage(
            url=p["urls"]["regular"],
            alt=p.get("alt_description") or keyword,
            credit=f"Photo by {p['user']['name']} on Unsplash",
        )
        for p in results
    ]