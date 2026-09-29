"""微信公众号草稿箱发布模块

功能：
- AI 生成封面图（OpenAI 兼容 / DashScope 通义万相 / Pillow 本地兜底）
- Markdown 转微信兼容 HTML（内联样式）
- 自动上传内容图片到微信
- 创建公众号草稿（不发布）
"""
from publish.publisher import publish_to_wechat, publish_report

__all__ = ["publish_to_wechat", "publish_report"]
