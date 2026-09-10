"""四个研究助理 Agent 定义"""
from agents.editor import create_editor
from agents.fact_checker import create_fact_checker
from agents.researcher import create_researcher
from agents.writer import create_writer

__all__ = [
    "create_researcher",
    "create_writer",
    "create_fact_checker",
    "create_editor",
]
