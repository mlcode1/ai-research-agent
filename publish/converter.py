"""Markdown → 微信公众号 HTML 转换器

微信公众号要求：
- 只能用内联样式（不支持 <style>、<link>、class）
- 图片必须来自 mmbiz.qpic.cn
- 不支持 JavaScript
- 部分 HTML 标签会被过滤
"""
import re
from pathlib import Path

import markdown
from bs4 import BeautifulSoup, NavigableString, Tag


# 微信兼容的内联样式
STYLES = {
    "body": "margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:16px;line-height:1.8;color:#333;",
    "h1": "font-size:24px;font-weight:700;color:#1a1a1a;margin:32px 0 16px;padding-bottom:8px;border-bottom:2px solid #4A90D9;",
    "h2": "font-size:20px;font-weight:700;color:#1a1a1a;margin:28px 0 12px;padding-left:12px;border-left:4px solid #4A90D9;",
    "h3": "font-size:18px;font-weight:600;color:#2c2c2c;margin:24px 0 10px;",
    "h4": "font-size:16px;font-weight:600;color:#333;margin:20px 0 8px;",
    "p": "margin:12px 0;line-height:1.8;",
    "p_in_li": "margin:4px 0;line-height:1.8;",  # 列表项内的段落
    "blockquote": "margin:16px 0;padding:12px 16px;background:#f7f8fa;border-left:4px solid #4A90D9;color:#666;font-size:15px;line-height:1.7;",
    "code_inline": "background:#f5f5f5;padding:2px 6px;border-radius:3px;font-family:Menlo,Consolas,'Courier New',monospace;font-size:14px;color:#c7254e;",
    "code_block": "background:#f8f8f8;padding:16px;border-radius:6px;font-family:Menlo,Consolas,'Courier New',monospace;font-size:13px;line-height:1.6;overflow-x:auto;white-space:pre-wrap;word-break:break-all;border:1px solid #e0e0e0;",
    "table": "width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;",
    "th": "background:#f5f7fa;padding:10px 12px;border:1px solid #ddd;font-weight:600;text-align:left;",
    "td": "padding:10px 12px;border:1px solid #ddd;",
    "ul": "margin:12px 0;padding-left:28px;",
    "ol": "margin:12px 0;padding-left:28px;",
    "li": "margin:6px 0;line-height:1.8;",
    "hr": "border:none;border-top:1px solid #e8e8e8;margin:28px 0;",
    "a": "color:#4A90D9;text-decoration:none;",
    "strong": "font-weight:700;color:#1a1a1a;",
    "img": "max-width:100%;height:auto;display:block;margin:16px auto;border-radius:4px;",
}


def md_to_wechat_html(md_text: str, image_map: dict | None = None) -> str:
    """把 Markdown 转成微信公众号兼容的 HTML

    Args:
        md_text: Markdown 原文
        image_map: {原始图片路径/URL: 微信 mmbiz URL} 映射，
                   传入后会替换正文中的 img src

    Returns:
        微信兼容的 HTML 字符串（带内联样式）
    """
    # Markdown → HTML
    extensions = ["tables", "fenced_code", "codehilite", "sane_lists"]
    raw_html = markdown.markdown(md_text, extensions=extensions)

    soup = BeautifulSoup(raw_html, "html.parser")

    # 清理空元素（在应用样式之前）
    _clean_empty_elements(soup)

    # 替换图片 URL
    if image_map:
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src in image_map:
                img["src"] = image_map[src]

    # 为所有元素注入内联样式
    _apply_styles(soup)
    
    # 优化信息来源部分的间距
    _compact_sources_section(soup)

    # 包裹在 section 里（微信编辑器推荐用 section 而非 div）
    content = str(soup)
    wrapped = f'<section style="{STYLES["body"]}">{content}</section>'

    return wrapped


def extract_title(md_text: str, fallback: str = "研究报告") -> str:
    """从 Markdown 中提取标题

    优先级：H1 > H2 > 文件名兜底
    """
    # 匹配 # 标题
    m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # 匹配 ## 标题
    m = re.search(r"^##\s+(.+)$", md_text, re.MULTILINE)
    if m:
        return m.group(1).strip()

    return fallback


def extract_digest(md_text: str, max_chars: int = 60, max_bytes: int = 180) -> str:
    """从 Markdown 中提取摘要（纯文本，去格式）

    用于微信草稿的 digest 字段（微信 API 限制：字符数约 60，字节数约 180）。

    Args:
        md_text: Markdown 文本
        max_chars: 最大字符数，默认 60
        max_bytes: 最大 UTF-8 字节数，默认 180

    Returns:
        摘要字符串，超限时自动截断并加 …
    """
    # 去掉 markdown 标记
    text = re.sub(r"^[#>*\-|`]", "", md_text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # 链接 → 文本
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)  # 去掉图片
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 跳过空行和纯标记行，取第一段有效文本
    result = ""
    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 20 and not line.startswith(("—", "=", "-", "```")):
            result = line
            break
    
    if not result:
        result = text
    
    # 按字符数截断
    if len(result) > max_chars:
        result = result[:max_chars - 1] + "…"
    
    # 按字节数检查（UTF-8 中文 3 字节/字）
    while len(result.encode('utf-8')) > max_bytes and len(result) > 10:
        result = result[:-2] + "…" if result[-1] == "…" else result[:-1] + "…"
    
    return result


def find_images(md_text: str) -> list[str]:
    """提取 Markdown 中所有图片路径/URL"""
    return re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md_text)


# ── 内部实现 ───────────────────────────────────────────────


def _clean_empty_elements(soup: BeautifulSoup):
    """清理内容为空的元素（如空的 <li>、<p> 等），防止渲染出空白行"""
    # 需要清理的标签
    tags_to_check = ["li", "p", "span"]
    
    for tag_name in tags_to_check:
        for tag in soup.find_all(tag_name):
            # 获取纯文本内容
            text = tag.get_text().strip()
            
            # 检查是否有实质性子元素（如图片、表格等）
            has_substantive_child = False
            for child in tag.descendants:
                if isinstance(child, Tag) and child.name in ["img", "table", "pre", "iframe"]:
                    has_substantive_child = True
                    break
            
            # 如果文本为空且没有实质性子元素，则移除该标签
            if not text and not has_substantive_child:
                tag.decompose()


def _apply_styles(soup: BeautifulSoup):
    """递归为所有元素注入内联样式"""
    tag_map = {
        "h1": STYLES["h1"],
        "h2": STYLES["h2"],
        "h3": STYLES["h3"],
        "h4": STYLES["h4"],
        "blockquote": STYLES["blockquote"],
        "table": STYLES["table"],
        "th": STYLES["th"],
        "td": STYLES["td"],
        "ul": STYLES["ul"],
        "ol": STYLES["ol"],
        "li": STYLES["li"],
        "hr": STYLES["hr"],
        "a": STYLES["a"],
        "strong": STYLES["strong"],
        "b": STYLES["strong"],
        "img": STYLES["img"],
    }

    for tag_name, style in tag_map.items():
        for tag in soup.find_all(tag_name):
            existing = tag.get("style", "")
            if existing:
                tag["style"] = f"{existing.rstrip(';')};{style}"
            else:
                tag["style"] = style
            # 微信不允许 class 属性
            if tag.has_attr("class"):
                del tag["class"]

    # 处理段落标签：区分普通段落和列表项内的段落
    for p in soup.find_all("p"):
        # 检查是否在列表项内
        parent = p.parent
        is_in_li = False
        while parent:
            if parent.name == "li":
                is_in_li = True
                break
            parent = parent.parent
        
        # 应用不同的样式
        style = STYLES["p_in_li"] if is_in_li else STYLES["p"]
        existing = p.get("style", "")
        if existing:
            p["style"] = f"{existing.rstrip(';')};{style}"
        else:
            p["style"] = style
        
        if p.has_attr("class"):
            del p["class"]

    # code 标签区分行内和块级
    for code in soup.find_all("code"):
        if code.parent and code.parent.name == "pre":
            code["style"] = STYLES["code_block"]
            code.parent["style"] = STYLES["code_block"]
            if code.parent.has_attr("class"):
                del code.parent["class"]
        else:
            code["style"] = STYLES["code_inline"]
        if code.has_attr("class"):
            del code["class"]

    # 清理微信不支持的属性
    for tag in soup.find_all(True):
        for attr in list(tag.attrs.keys()):
            if attr not in ("style", "src", "href", "alt", "width", "height"):
                del tag[attr]


def _compact_sources_section(soup: BeautifulSoup):
    """压缩信息来源部分的间距，减少空白"""
    # 查找"信息来源"标题
    sources_heading = None
    for h2 in soup.find_all("h2"):
        if "信息来源" in h2.get_text() or "参考资料" in h2.get_text() or "参考链接" in h2.get_text():
            sources_heading = h2
            break
    
    if not sources_heading:
        return
    
    # 找到标题后的所有兄弟元素，减少它们的间距
    for sibling in sources_heading.find_next_siblings():
        # 减少 <p> 和 <ul> 的 margin
        if sibling.name in ("p", "ul", "ol"):
            sibling["style"] = "margin:2px 0;line-height:1.5;"
        
        # 减少列表项的间距
        if sibling.name in ("ul", "ol"):
            for li in sibling.find_all("li"):
                li["style"] = "margin:1px 0;line-height:1.5;font-size:14px;"
