#!/usr/bin/env python3
"""
微信公众号草稿功能独立测试脚本

用法:
    python test_wechat.py                          # 使用最新的报告
    python test_wechat.py <报告文件名>              # 指定报告文件
    
示例:
    python test_wechat.py "2026年AI工程师的发展之路-20260910-225129.md"
"""
import sys
from pathlib import Path
from publish import publish_report

def main():
    # 获取报告文件路径
    if len(sys.argv) > 1:
        # 用户指定了文件名
        filename = sys.argv[1]
        md_path = Path("output") / filename
    else:
        # 使用最新的报告
        output_dir = Path("output")
        md_files = sorted(output_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not md_files:
            print("❌ output/ 目录下没有找到任何报告文件")
            sys.exit(1)
        md_path = md_files[0]
    
    # 检查文件是否存在
    if not md_path.exists():
        print(f"❌ 文件不存在: {md_path}")
        sys.exit(1)
    
    print(f"📄 测试报告: {md_path.name}")
    print("=" * 60)
    
    # 调用发布函数
    try:
        result = publish_report(str(md_path))
        print("=" * 60)
        if result.get("success"):
            print("✅ 测试成功！草稿已创建")
            print(f"📝 标题: {result.get('title')}")
            print(f"🎨 封面图: {result.get('cover_image_url')}")
            print(f"🔗 草稿链接: {result.get('draft_url')}")
        else:
            print("❌ 测试失败")
            print(f"错误信息: {result.get('error', '未知错误')}")
    except Exception as e:
        print("=" * 60)
        print(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
