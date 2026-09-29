"""微信公众号 API 客户端

封装 access_token 管理、素材上传、草稿创建等接口。
文档：https://developers.weixin.qq.com/doc/offiaccount/
"""
import json
import time
from pathlib import Path

import requests


def _truncate_utf8(text: str, max_bytes: int) -> str:
    """按 UTF-8 字节数截断字符串，确保不破坏多字节字符
    
    Args:
        text: 原始文本
        max_bytes: 最大字节数
        
    Returns:
        截断后的字符串
    """
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    
    # 逐字符累加字节数，找到安全截断点
    result = []
    current_bytes = 0
    
    for char in text:
        char_bytes = len(char.encode('utf-8'))
        if current_bytes + char_bytes > max_bytes:
            break
        result.append(char)
        current_bytes += char_bytes
    
    return ''.join(result)


class WeChatAPIError(Exception):
    """微信 API 错误"""


class WeChatAPI:
    """微信公众号 API 客户端"""

    BASE_URL = "https://api.weixin.qq.com/cgi-bin"

    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str = ""
        self._token_expires: float = 0

    # ── token 管理 ──────────────────────────────────────────

    def get_access_token(self) -> str:
        """获取 access_token（自动缓存，过期前 5 分钟刷新）"""
        now = time.time()
        if self._token and now < self._token_expires - 300:
            return self._token

        resp = requests.get(
            f"{self.BASE_URL}/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
            timeout=10,
        ).json()

        if "access_token" not in resp:
            raise WeChatAPIError(
                f"获取 access_token 失败：{resp.get('errcode')} - {resp.get('errmsg')}"
            )

        self._token = resp["access_token"]
        self._token_expires = now + resp.get("expires_in", 7200)
        return self._token

    # ── 素材上传 ────────────────────────────────────────────

    def upload_permanent_image(self, image_path: str | Path) -> str:
        """上传永久图片素材，返回 media_id（用于封面图 thumb_media_id）

        限制：每天 10 次（未认证号）或 100 次（认证号）
        """
        image_path = Path(image_path)
        token = self.get_access_token()

        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{self.BASE_URL}/material/add_material",
                params={"access_token": token, "type": "image"},
                files={"media": (image_path.name, f, "image/png")},
                timeout=30,
            ).json()

        if "media_id" not in resp:
            raise WeChatAPIError(
                f"上传封面图失败：{resp.get('errcode')} - {resp.get('errmsg')}"
            )

        return resp["media_id"]

    def upload_content_image(self, image_path: str | Path) -> str:
        """上传正文内嵌图片，返回 mmbiz URL（用于替换正文中的 img src）

        注意：此接口上传的图片不计入素材库配额
        """
        image_path = Path(image_path)
        token = self.get_access_token()

        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{self.BASE_URL}/media/uploadimg",
                params={"access_token": token},
                files={"media": (image_path.name, f, "image/png")},
                timeout=30,
            ).json()

        if "url" not in resp:
            raise WeChatAPIError(
                f"上传正文图片失败：{resp.get('errcode')} - {resp.get('errmsg')}"
            )

        return resp["url"]

    # ── 草稿箱 ──────────────────────────────────────────────

    def add_draft(
        self,
        title: str,
        content: str,
        thumb_media_id: str,
        author: str = "小马",
        digest: str = "",
        need_open_comment: int = 0,
        only_fans_can_comment: int = 0,
    ) -> str:
        """创建草稿，返回 media_id

        草稿创建后不会自动发布，需登录公众号后台手动发布。

        字段长度限制（微信 API）：
        - title: 64 字节
        - author: 8 字节（约 2-3 个中文字符）
        - digest: 120 字节（约 40 个中文字符）
        - content: 20000 字符以内
        """
        token = self.get_access_token()

        # 字段长度安全截断
        title = _truncate_utf8(title, max_bytes=64)
        author = _truncate_utf8(author, max_bytes=8)
        digest = _truncate_utf8(digest, max_bytes=120)

        article = {
            "title": title,
            "author": author,
            "digest": digest,
            "content": content,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": need_open_comment,
            "only_fans_can_comment": only_fans_can_comment,
        }

        resp = requests.post(
            f"{self.BASE_URL}/draft/add",
            params={"access_token": token},
            data=json.dumps({"articles": [article]}, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15,
        ).json()

        if "media_id" not in resp:
            raise WeChatAPIError(
                f"创建草稿失败：{resp.get('errcode')} - {resp.get('errmsg')}"
            )

        return resp["media_id"]
