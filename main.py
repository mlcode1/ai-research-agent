"""AI 研究助理 - CLI 入口

用法:
    python main.py "研究主题"
    python main.py --publish "研究主题"   # 生成后自动发布到微信公众号草稿箱
    python main.py --no-publish "研究主题" # 强制不发布
    python main.py                        # 交互式输入
"""
import re
import sys
from datetime import datetime

from crew import build_crew
from config import OUTPUT_DIR, WECHAT_ENABLED, WECHAT_APP_ID


def slugify(text: str) -> str:
    """把主题转成文件名安全的 slug"""
    # 保留中文、字母、数字、连字符
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]", "-", text.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:50] if slug else "report"


def _parse_args():
    """解析命令行参数，返回 (topic, publish_flag)

    publish_flag: True=强制发布, False=强制不发布, None=跟随配置
    """
    args = sys.argv[1:]
    publish = None

    if "--publish" in args:
        publish = True
        args.remove("--publish")
    elif "--no-publish" in args:
        publish = False
        args.remove("--no-publish")

    topic = " ".join(args).strip() if args else ""
    return topic, publish


def main():
    topic, publish_flag = _parse_args()

    # 交互式输入
    if not topic:
        topic = input("请输入研究主题：").strip()

    if not topic:
        print("错误：请提供研究主题")
        sys.exit(1)

    # 决定是否发布到微信
    if publish_flag is True:
        do_publish = True
    elif publish_flag is False:
        do_publish = False
    else:
        do_publish = WECHAT_ENABLED and bool(WECHAT_APP_ID)

    print(f"\n🐴 开始研究主题：{topic}")
    print("=" * 60)
    print("流程：研究员查资料 → 写作起草 → 事实核查 → 编辑润色")
    if do_publish:
        print("       → 📮 完成后自动发布到微信公众号草稿箱")
    print("预计耗时 2-5 分钟，取决于模型速度和搜索次数\n")

    # 构建并运行 crew
    crew = build_crew(topic)
    result = crew.kickoff()

    # 输出报告到文件
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{slugify(topic)}-{timestamp}.md"
    filepath = OUTPUT_DIR / filename

    report = str(result)
    
    # 强制清理标题前缀（移除「研究报告」等字样）
    from publish.publisher import clean_article_title
    cleaned_report = clean_article_title(report)
    if cleaned_report != report:
        print("🔧 已清理标题前缀")
        report = cleaned_report
    
    filepath.write_text(report, encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"✅ 报告已生成：{filepath}")
    print(f"📊 报告字数：{len(report)} 字符")
    print("=" * 60)

    # 发布到微信公众号草稿箱
    if do_publish:
        from publish import publish_report

        pub_result = publish_report(filepath, topic=topic)
        if pub_result["success"]:
            print(f"📮 微信草稿已创建：{pub_result['title']}")
            print(f"   封面图：{pub_result['cover_path']}")
        else:
            print(f"⚠️ 微信发布失败：{pub_result['error']}")


if __name__ == "__main__":
    main()
