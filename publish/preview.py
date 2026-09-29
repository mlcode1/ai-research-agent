"""微信公众号 HTML 预览工具

生成一个独立的 HTML 文件，模拟微信公众号文章的渲染效果。
在浏览器中打开即可预览，和草稿中的显示效果基本一致。
"""
from pathlib import Path
from datetime import datetime


# 模拟微信公众号阅读页的样式（仅用于预览，不会发送到微信）
_PREVIEW_WRAPPER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 微信预览</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #f5f5f5;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  }}
  .preview-container {{
    max-width: 580px;
    margin: 20px auto;
    background: #fff;
    padding: 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  }}
  .preview-header {{
    background: #07c160;
    color: #fff;
    padding: 12px 16px;
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .preview-header::before {{
    content: "📱";
    font-size: 18px;
  }}
  .preview-meta {{
    padding: 20px 16px 10px;
    border-bottom: 1px solid #f0f0f0;
  }}
  .preview-meta h1 {{
    font-size: 22px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 12px;
    line-height: 1.4;
  }}
  .preview-meta .meta-info {{
    font-size: 13px;
    color: #999;
    display: flex;
    gap: 16px;
  }}
  .preview-content {{
    padding: 16px;
  }}
  .preview-footer {{
    padding: 16px;
    border-top: 1px solid #f0f0f0;
    text-align: center;
    color: #999;
    font-size: 12px;
  }}
</style>
</head>
<body>
<div class="preview-container">
  <div class="preview-header">微信公众号文章预览</div>
  <div class="preview-meta">
    <h1>{title}</h1>
    <div class="meta-info">
      <span>作者：{author}</span>
      <span>{date}</span>
    </div>
  </div>
  <div class="preview-content">
    {content}
  </div>
  <div class="preview-footer">
    以上为微信公众号草稿预览效果，实际显示可能因客户端版本略有差异
  </div>
</div>
</body>
</html>"""


def generate_preview(
    html_content: str,
    title: str,
    output_path: str | Path,
    author: str = "小马",
) -> Path:
    """生成微信预览 HTML 文件
    
    Args:
        html_content: 微信兼容的 HTML 内容
        title: 文章标题
        output_path: 预览文件保存路径
        author: 作者名
        
    Returns:
        预览文件路径
    """
    output_path = Path(output_path)
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    date = datetime.now().strftime("%Y-%m-%d")
    
    full_html = _PREVIEW_WRAPPER.format(
        title=title,
        author=author,
        date=date,
        content=html_content,
    )
    
    output_path.write_text(full_html, encoding="utf-8")
    return output_path
