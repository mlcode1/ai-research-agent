"""AI 研究助理 - CLI 入口

用法:
    python main.py "研究主题"
    python main.py                    # 交互式输入
"""
import re
import sys
from datetime import datetime

from crew import build_crew
from config import OUTPUT_DIR


def slugify(text: str) -> str:
    """把主题转成文件名安全的 slug"""
    # 保留中文、字母、数字、连字符
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]", "-", text.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:50] if slug else "report"


def main():
    # 获取主题
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:]).strip()
    else:
        topic = input("请输入研究主题：").strip()

    if not topic:
        print("错误：请提供研究主题")
        sys.exit(1)

    print(f"\n🐴 开始研究主题：{topic}")
    print("=" * 60)
    print("流程：研究员查资料 → 写作起草 → 事实核查 → 编辑润色")
    print("预计耗时 2-5 分钟，取决于模型速度和搜索次数\n")

    # 构建并运行 crew
    crew = build_crew(topic)
    result = crew.kickoff()

    # 输出报告到文件
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{slugify(topic)}-{timestamp}.md"
    filepath = OUTPUT_DIR / filename

    report = str(result)
    filepath.write_text(report, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ 报告已生成：{filepath}")
    print(f"📊 报告字数：{len(report)} 字符")
    print("=" * 60)


if __name__ == "__main__":
    main()
