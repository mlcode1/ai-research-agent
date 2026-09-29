"""AI 封面图生成

支持三种方式：
1. OpenAI 兼容 API（通用，支持 DashScope/SiliconFlow 等）
2. DashScope 通义万相（异步 API）
3. Pillow 本地兜底（专业排版：标题 + 关键词标签 + 装饰元素）
"""
import re
import time
import hashlib
from pathlib import Path

import requests


def generate_cover(
    topic: str,
    output_path: str | Path,
    provider: str = "auto",
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    style: str = "简约、扁平设计、柔和渐变背景、干净现代",
    md_text: str = "",
) -> Path:
    """生成封面图，返回本地文件路径

    Args:
        topic: 报告主题/标题
        output_path: 图片保存路径
        provider: auto / openai_compatible / dashscope / pillow
        api_key: 图片生成 API key
        base_url: OpenAI 兼容 API 地址
        model: 模型名
        style: 风格描述
        md_text: 报告 Markdown 原文（用于提取关键词和生成 AI prompt）
    """
    output_path = Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # 从文章内容提取关键词，用于 AI prompt 和 Pillow 排版
    keywords = _extract_keywords(topic, md_text) if md_text else [topic]

    # 构建 AI 生图 prompt（基于文章内容而非仅主题）
    prompt = _build_ai_prompt(topic, keywords, style)

    if provider == "auto":
        for method in [_openai_compatible, _dashscope_async, _pillow_fallback]:
            try:
                method(topic, prompt, output_path, api_key, base_url, model, style, keywords)
                return output_path
            except Exception:
                continue
        _pillow_fallback(topic, prompt, output_path, api_key, base_url, model, style, keywords)
        return output_path

    dispatch = {
        "openai_compatible": _openai_compatible,
        "dashscope": _dashscope_async,
        "pillow": _pillow_fallback,
    }
    fn = dispatch.get(provider, _pillow_fallback)
    fn(topic, prompt, output_path, api_key, base_url, model, style, keywords)
    return output_path


# ── 方式 1：OpenAI 兼容 API ────────────────────────────────


def _openai_compatible(topic, prompt, output_path, api_key, base_url, model, style, keywords=None):
    """OpenAI 兼容的图片生成 API（同步）"""
    if not api_key or not base_url:
        raise ValueError("未配置 COVER_IMAGE_API_KEY 或 COVER_IMAGE_BASE_URL")

    model = model or "wanx-v1"

    resp = requests.post(
        f"{base_url}/images/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": "1280x720",
            "response_format": "url",
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    image_url = data["data"][0]["url"]
    _download_image(image_url, output_path)


# ── 方式 2：DashScope 通义万相（异步 API）──────────────────


def _dashscope_async(topic, prompt, output_path, api_key, base_url, model, style, keywords=None):
    """DashScope 通义万相（异步提交 + 轮询）"""
    if not api_key:
        raise ValueError("未配置 COVER_IMAGE_API_KEY")

    model = model or "wanx-v1"

    submit_resp = requests.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        },
        json={
            "model": model,
            "input": {"prompt": prompt},
            "parameters": {"size": "1280*720", "n": 1},
        },
        timeout=15,
    )
    submit_resp.raise_for_status()
    task_id = submit_resp.json()["output"]["task_id"]

    for _ in range(40):
        time.sleep(3)
        status_resp = requests.get(
            f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        ).json()

        status = status_resp["output"]["task_status"]
        if status == "SUCCEEDED":
            image_url = status_resp["output"]["results"][0]["url"]
            _download_image(image_url, output_path)
            return
        elif status == "FAILED":
            raise RuntimeError(f"通义万相生成失败：{status_resp}")

    raise TimeoutError("通义万相生成超时（2 分钟）")


# ── 方式 3：Pillow 本地兜底（专业排版）─────────────────────


# 预定义配色方案（左侧装饰带颜色 + 右侧背景色）
_PALETTES = [
    # (accent_r, accent_g, accent_b, bg_r, bg_g, bg_b)
    (52, 73, 94, 245, 247, 250),     # 深青灰 + 浅灰白（商务）
    (44, 62, 80, 236, 240, 241),     # 深靛蓝 + 浅灰（科技）
    (39, 174, 96, 250, 252, 248),    # 翠绿 + 米白（自然/环保）
    (142, 68, 173, 248, 245, 252),   # 紫色 + 浅紫灰（创新）
    (211, 84, 0, 255, 248, 243),     # 橙色 + 暖白（活力）
    (41, 128, 185, 243, 248, 252),   # 天蓝 + 浅蓝灰（清新）
    (192, 57, 43, 252, 245, 243),    # 红色 + 暖灰（热点）
    (22, 160, 133, 245, 250, 248),   # 青色 + 浅青灰（数据）
]


def _pillow_fallback(topic, prompt, output_path, api_key, base_url, model, style, keywords=None):
    """Pillow 生成专业排版封面（基于文章内容提取关键词）

    布局：左侧色带（含标题）+ 右侧白色区域（含关键词标签 + 装饰元素）
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = 1280, 720
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 根据主题哈希选配色（同一主题每次生成一样的封面）
    palette_idx = int(hashlib.md5(topic.encode()).hexdigest(), 16) % len(_PALETTES)
    accent_r, accent_g, accent_b, bg_r, bg_g, bg_b = _PALETTES[palette_idx]

    # 右侧背景（浅色系）
    draw.rectangle([(0, 0), (width, height)], fill=(bg_r, bg_g, bg_b))

    # 左侧装饰带（占 38% 宽度）
    left_w = int(width * 0.38)
    # 渐变效果
    for x in range(left_w):
        ratio = x / left_w
        r = int(accent_r * (0.85 + ratio * 0.15))
        g = int(accent_g * (0.85 + ratio * 0.15))
        b = int(accent_b * (0.85 + ratio * 0.15))
        r = min(r, 255)
        g = min(g, 255)
        b = min(b, 255)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))

    # 加载字体
    title_font = _load_font(size=36)
    label_font = _load_font(size=16)
    tag_font = _load_font(size=18)
    small_font = _load_font(size=14)

    # ── 左侧：标题 + 装饰 ──
    # 顶部小标签（白色半透明 → 与中间色混合）
    mid_accent = _blend_color((255, 255, 255), (accent_r, accent_g, accent_b), alpha=0.70)
    soft_white = _blend_color((255, 255, 255), (accent_r, accent_g, accent_b), alpha=0.63)
    dim_white = _blend_color((255, 255, 255), (accent_r, accent_g, accent_b), alpha=0.39)

    draw.text((50, 50), "研究报告", fill=mid_accent, font=label_font)
    # 分隔线
    draw.rectangle([(50, 80), (120, 83)], fill=soft_white)

    # 标题（自动换行）
    title_lines = _wrap_text(draw, topic, title_font, max_width=left_w - 100)
    y_start = 110
    for i, line in enumerate(title_lines[:5]):  # 最多 5 行
        draw.text((50, y_start + i * 48), line, fill=(255, 255, 255), font=title_font)

    # 底部装饰：细线 + 日期
    from datetime import datetime
    date_str = datetime.now().strftime("%Y.%m.%d")
    draw.rectangle([(50, height - 70), (left_w - 50, height - 68)], fill=dim_white)
    draw.text((50, height - 55), date_str, fill=soft_white, font=small_font)

    # ── 右侧：关键词标签 + 装饰 ──
    right_x = left_w + 60
    kw = keywords or [topic]

    # 关键词区域标题
    draw.text((right_x, 200), "关键词", fill=(accent_r, accent_g, accent_b), font=label_font)
    draw.rectangle([(right_x, 225), (right_x + 40, 228)], fill=(accent_r, accent_g, accent_b))

    # 关键词标签（圆角矩形 + 文字）
    tag_y = 260
    tag_x = right_x
    max_tag_x = width - 60

    # 预计算半透明颜色（RGB 模式不支持 alpha，手动混合）
    tag_bg = _blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.10)
    tag_border = _blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.30)

    for word in kw[:8]:  # 最多 8 个关键词
        # 计算标签宽度
        bbox = draw.textbbox((0, 0), word, font=tag_font)
        tw = bbox[2] - bbox[0]
        tag_w = tw + 30
        tag_h = 36

        # 换行检测
        if tag_x + tag_w > max_tag_x:
            tag_x = right_x
            tag_y += tag_h + 14

        # 画圆角标签背景
        _draw_rounded_rect(
            draw,
            (tag_x, tag_y, tag_x + tag_w, tag_y + tag_h),
            radius=6,
            fill=tag_bg,
            outline=tag_border,
        )
        # 标签文字
        draw.text((tag_x + 15, tag_y + 7), word, fill=(accent_r, accent_g, accent_b), font=tag_font)
        tag_x += tag_w + 14

    # 右侧装饰：几何元素
    # 右上角大圆（半透明）
    _draw_circle(draw, (width - 120, -40), 160,
                 fill=_blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.05))
    # 右下角小圆
    _draw_circle(draw, (width - 80, height - 80), 60,
                 fill=_blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.07))
    # 中间散点
    for dx, dy, dr in [(right_x + 300, 480, 8), (right_x + 380, 520, 5), (right_x + 260, 540, 6)]:
        _draw_circle(draw, (dx, dy), dr,
                     fill=_blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.12))

    # 右下角装饰线
    draw.rectangle(
        [(right_x, height - 50), (right_x + 60, height - 48)],
        fill=_blend_color((accent_r, accent_g, accent_b), (bg_r, bg_g, bg_b), alpha=0.23),
    )

    img.save(str(output_path), "PNG", quality=95)


# ── 工具函数 ───────────────────────────────────────────────


def _extract_keywords(topic: str, md_text: str) -> list[str]:
    """从文章 Markdown 中提取关键词（用于封面图排版和 AI 生图 prompt）

    策略：
    1. 提取 ## 和 ### 标题作为候选关键词
    2. 提取「」和 **加粗** 中的短语
    3. 统计高频词（去停用词）
    4. 返回 3-8 个关键词
    """
    candidates = []

    # 1. 标题作为关键词
    headings = re.findall(r"^#{2,3}\s+(.+)$", md_text, re.MULTILINE)
    for h in headings[:6]:
        h = h.strip()
        # 去掉 markdown 格式
        h = re.sub(r"\*\*([^*]+)\*\*", r"\1", h)
        if len(h) <= 15:
            candidates.append(h)

    # 2. 加粗文本和引号内容
    bold_texts = re.findall(r"\*\*([^*]{2,12})\*\*", md_text)
    quoted_texts = re.findall(r"[「「]([^」」]{2,10})[」」]", md_text)
    candidates.extend(bold_texts[:10])
    candidates.extend(quoted_texts[:10])

    # 3. 统计词频（中文 2-6 字词组）
    clean_text = re.sub(r"#{1,6}\s*", "", md_text)  # 去标题标记
    clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean_text)  # 链接转文本
    clean_text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", clean_text)  # 去图片
    clean_text = re.sub(r"[^\w\u4e00-\u9fff\s]", " ", clean_text)

    # 提取中文词组（简单 n-gram）
    word_freq: dict[str, int] = {}
    chinese_segments = re.findall(r"[\u4e00-\u9fff]{2,6}", clean_text)
    stop_words = {
        "的是", "可以", "已经", "进行", "通过", "其中", "以及", "对于",
        "但是", "而且", "如果", "因为", "所以", "不是", "没有", "这个",
        "那个", "他们", "我们", "他们", "这些", "那些", "一个", "两个",
        "报告", "数据", "分析", "发展", "趋势", "技术", "行业", "市场",
    }
    for w in chinese_segments:
        if w not in stop_words:
            word_freq[w] = word_freq.get(w, 0) + 1

    # 按频率排序，取 top
    top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:15]
    candidates.extend([w for w, _ in top_words])

    # 去重，保持顺序
    seen = set()
    unique = []
    for c in candidates:
        c = c.strip()
        if c and c not in seen and len(c) >= 2:
            seen.add(c)
            unique.append(c)

    return unique[:8]


def _build_ai_prompt(topic: str, keywords: list[str], style: str) -> str:
    """基于文章内容构建 AI 生图 prompt"""
    kw_str = "、".join(keywords[:5])
    return (
        f"A professional cover image for a research report. "
        f"Topic: {topic}. Key themes: {kw_str}. "
        f"Style: {style}, professional business style, suitable for WeChat article cover. "
        f"Abstract conceptual illustration related to the topic, no text or letters."
    )


def _download_image(url: str, save_path: Path):
    """下载图片到本地"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)


def _blend_color(fg: tuple, bg: tuple, alpha: float) -> tuple:
    """颜色混合（模拟半透明效果）
    
    Args:
        fg: 前景色 RGB 三元组
        bg: 背景色 RGB 三元组
        alpha: 前景色透明度 (0.0-1.0)
    
    Returns:
        混合后的 RGB 三元组
    """
    return tuple(
        int(f * alpha + b * (1 - alpha))
        for f, b in zip(fg, bg)
    )


def _load_font(size: int):
    """尝试加载中文字体"""
    from PIL import ImageFont

    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for fp in font_paths:
        try:
            return ImageFont.truetype(fp, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    """将文本按宽度自动换行"""
    lines = []
    current = ""
    for char in text:
        test = current + char
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_rounded_rect(draw, bbox, radius, fill, outline=None):
    """画圆角矩形"""
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline)


def _draw_circle(draw, center, radius, fill):
    """画圆（fill 应该是已经混合好的 RGB 三元组）"""
    cx, cy = center
    x0, y0 = cx - radius, cy - radius
    x1, y1 = cx + radius, cy + radius
    draw.ellipse([(x0, y0), (x1, y1)], fill=fill)
