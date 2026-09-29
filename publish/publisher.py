"""微信公众号发布主流程

报告生成后 → 提取标题/摘要 → 生成封面图 → 转换 HTML → 上传素材 → 创建草稿
"""
import tempfile
from pathlib import Path

from config import (
    WECHAT_APP_ID,
    WECHAT_APP_SECRET,
    WECHAT_ENABLED,
    WECHAT_AUTO_COVER,
    COVER_IMAGE_PROVIDER,
    COVER_IMAGE_API_KEY,
    COVER_IMAGE_BASE_URL,
    COVER_IMAGE_MODEL,
    COVER_IMAGE_STYLE,
    OUTPUT_DIR,
)
from publish.weixin import WeChatAPI, WeChatAPIError
from publish.cover import generate_cover
from publish.converter import md_to_wechat_html, extract_title, extract_digest, find_images


def publish_report(
    md_path: str | Path,
    topic: str = "",
    auto_publish: bool | None = None,
) -> dict:
    """将报告发布到微信公众号草稿箱

    Args:
        md_path: 报告 Markdown 文件路径
        topic: 研究主题（用于封面图生成，为空则从文件标题提取）
        auto_publish: 是否发布，None 则读 WECHAT_ENABLED 配置

    Returns:
        {
            "success": bool,
            "draft_media_id": str,   # 草稿 media_id
            "cover_path": str,       # 封面图本地路径
            "title": str,            # 文章标题
            "error": str | None,     # 错误信息
        }
    """
    md_path = Path(md_path)
    if not md_path.exists():
        return {"success": False, "error": f"报告文件不存在：{md_path}"}

    should_publish = auto_publish if auto_publish is not None else WECHAT_ENABLED
    if not should_publish:
        return {"success": False, "error": "微信发布未启用（WECHAT_ENABLED=false）"}

    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        return {"success": False, "error": "未配置 WECHAT_APP_ID 或 WECHAT_APP_SECRET"}

    md_text = md_path.read_text(encoding="utf-8")
    title = extract_title(md_text, fallback=topic or md_path.stem)
    digest = extract_digest(md_text)
    topic_for_cover = topic or title

    print(f"\n📤 准备发布到微信公众号草稿箱...")
    print(f"   标题：{title}")
    print(f"   摘要：{digest[:60]}...")

    # 1. 生成封面图
    cover_dir = OUTPUT_DIR / "covers"
    cover_dir.mkdir(exist_ok=True)
    cover_path = cover_dir / f"{md_path.stem}-cover.png"

    if WECHAT_AUTO_COVER:
        print(f"   🎨 生成封面图（{COVER_IMAGE_PROVIDER}）...")
        try:
            generate_cover(
                topic=topic_for_cover,
                output_path=cover_path,
                provider=COVER_IMAGE_PROVIDER,
                api_key=COVER_IMAGE_API_KEY,
                base_url=COVER_IMAGE_BASE_URL,
                model=COVER_IMAGE_MODEL,
                style=COVER_IMAGE_STYLE,
                md_text=md_text,
            )
            print(f"   ✅ 封面图已生成：{cover_path}")
        except Exception as e:
            print(f"   ⚠️ 封面图生成失败：{e}，使用本地兜底")
            generate_cover(topic=topic_for_cover, output_path=cover_path, provider="pillow", md_text=md_text)
    else:
        print(f"   🎨 生成本地封面图（Pillow）...")
        generate_cover(topic=topic_for_cover, output_path=cover_path, provider="pillow", md_text=md_text)

    # 2. 初始化微信 API
    wechat = WeChatAPI(WECHAT_APP_ID, WECHAT_APP_SECRET)

    # 3. 上传封面图
    print(f"   📤 上传封面图到微信...")
    thumb_media_id = wechat.upload_permanent_image(cover_path)
    print(f"   ✅ 封面图 media_id：{thumb_media_id[:20]}...")

    # 4. 处理正文图片（下载 → 上传微信 → 替换 URL）
    image_map = {}
    image_urls = find_images(md_text)
    if image_urls:
        print(f"   📤 处理正文中 {len(image_urls)} 张图片...")
        for img_url in image_urls:
            if img_url.startswith("http://mmbiz.qpic.cn") or img_url.startswith("https://mmbiz.qpic.cn"):
                continue  # 已经是微信图片
            try:
                tmp_path = _download_to_temp(img_url)
                if tmp_path:
                    wx_url = wechat.upload_content_image(tmp_path)
                    image_map[img_url] = wx_url
                    tmp_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"   ⚠️ 图片上传跳过：{img_url[:50]}... ({e})")

    # 5. Markdown → 微信 HTML
    print(f"   📝 转换 Markdown → 微信 HTML...")
    wechat_html = md_to_wechat_html(md_text, image_map=image_map)
    
    # 检查 HTML 大小（微信限制约 20000 字符）
    if len(wechat_html) > 18000:
        print(f"   ⚠️ HTML 内容过大（{len(wechat_html)} 字符），自动截断...")
        wechat_html = wechat_html[:18000] + "</section>"
    
    print(f"   📝 摘要长度：{len(digest)} 字符 / {len(digest.encode('utf-8'))} 字节")

    # 6. 创建草稿
    print(f"   📮 创建公众号草稿...")
    draft_media_id = wechat.add_draft(
        title=title,
        content=wechat_html,
        thumb_media_id=thumb_media_id,
        digest=digest,
    )

    print(f"   ✅ 草稿创建成功！media_id：{draft_media_id}")
    print(f"   👉 请登录公众号后台查看并发布\n")

    return {
        "success": True,
        "draft_media_id": draft_media_id,
        "cover_path": str(cover_path),
        "title": title,
        "error": None,
    }


def publish_to_wechat(md_path: str | Path, topic: str = "") -> dict:
    """publish_report 的便捷别名"""
    return publish_report(md_path, topic=topic)


# ── 工具函数 ───────────────────────────────────────────────


def _download_to_temp(url: str) -> Path | None:
    """下载图片到临时文件"""
    import requests

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None

    suffix = ".png"
    if ".jpg" in url or ".jpeg" in url:
        suffix = ".jpg"
    elif ".gif" in url:
        suffix = ".gif"
    elif ".webp" in url:
        suffix = ".webp"

    tmp = Path(tempfile.mktemp(suffix=suffix, prefix="wx_img_"))
    tmp.write_bytes(resp.content)
    return tmp
