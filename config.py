"""配置文件 - LLM、搜索、输出目录设置"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# ===== LLM 配置 =====
# 默认 DeepSeek（便宜 + 国内访问方便），兼容 OpenAI 格式 API
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")

# ===== 搜索配置 =====
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
# 不填则用 DuckDuckGo 免费搜索，填了用 Tavily（更稳定）
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ===== 输出目录 =====
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def get_llm():
    """返回共享的 CrewAI LLM 实例。

    使用 LiteLLM 格式：model = "provider/model_name"
    通过 base_url 指向 OpenAI 兼容 endpoint，支持 DeepSeek/通义/Moonshot 等。
    """
    if not LLM_API_KEY:
        raise ValueError(
            "未配置 LLM_API_KEY，请复制 .env.example 为 .env 并填入 API key。"
            "默认用 DeepSeek，注册地址：https://platform.deepseek.com"
        )

    from crewai import LLM

    model = f"{LLM_PROVIDER}/{LLM_MODEL}" if LLM_PROVIDER else LLM_MODEL
    return LLM(
        model=model,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
    )
