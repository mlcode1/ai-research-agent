"""Streamlit 可视化界面 - 浏览器里运行研究助理

运行：
    streamlit run app.py
"""
import re
from datetime import datetime

import streamlit as st

from config import (
    LLM_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    OUTPUT_DIR,
    WECHAT_ENABLED,
    WECHAT_APP_ID,
)
from crew import build_crew


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff\-]", "-", text.strip())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:50] if slug else "report"


def main():
    st.set_page_config(page_title="AI 研究助理", page_icon="🐴", layout="wide")
    st.title("🐴 AI 研究助理")
    st.caption("多智能体协作出研究报告：研究员 → 写作 → 事实核查 → 编辑")

    # 侧边栏：配置状态 + 历史
    with st.sidebar:
        st.header("配置状态")
        st.write(f"**模型**: `{LLM_PROVIDER}/{LLM_MODEL}`")
        st.write(f"**API Key**: {'✅ 已配置' if LLM_API_KEY else '❌ 未配置'}")

        # 微信发布状态
        wechat_ok = WECHAT_ENABLED and bool(WECHAT_APP_ID)
        st.write(f"**微信发布**: {'✅ 已启用' if wechat_ok else '⚪ 未启用'}")

        if not LLM_API_KEY:
            st.error("请先配置 .env 的 LLM_API_KEY")
            st.code("cp .env.example .env\n# 编辑 .env 填入 DeepSeek/OpenAI key")
            st.stop()
        st.divider()
        st.write("📁 报告输出到 `output/`")
        # 显示已有报告
        reports = sorted(OUTPUT_DIR.glob("*.md"), reverse=True)
        if reports:
            st.write(f"📄 已有 {len(reports)} 份报告")
            for r in reports[:5]:
                st.write(f"- {r.name}")

    # 主题输入
    topic = st.text_input(
        "研究主题",
        placeholder=f"例：AI Agent 在 {datetime.now().year} 年的最新发展趋势",
    )

    examples = [
        f"AI Agent 在 {datetime.now().year} 年的最新发展趋势",
        "DeepSeek 对中国 AI 行业的影响",
        "开源 vs 闭源大模型的商业化对比",
    ]
    cols = st.columns(3)
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"ex_{i}"):
            st.session_state.topic_input = ex
            st.rerun()

    # 发布选项
    wechat_ok = WECHAT_ENABLED and bool(WECHAT_APP_ID)
    publish_to_wechat = False
    if wechat_ok:
        publish_to_wechat = st.checkbox(
            "📮 生成后发布到微信公众号草稿箱",
            value=True,
            help="报告生成后自动生成封面图并推送到草稿箱（不会自动发布）",
        )

    if st.button("🚀 开始研究", type="primary", disabled=not topic.strip()):
        _run_research(topic.strip(), publish_to_wechat=publish_to_wechat)


def _run_research(topic: str, publish_to_wechat: bool = False):
    st.info(f"开始研究「{topic}」，预计 2-5 分钟...")

    progress = st.progress(0.0, text="正在启动研究 Crew...")
    status_box = st.empty()

    # 四个 agent 的进度文案
    stage_labels = {
        "资深研究员": "🔎 研究员收集资料中...",
        "专业报告写作": "✍️ 写作起草报告中...",
        "事实核查员": "🔍 事实核查中...",
        "终稿编辑": "📝 编辑润色终稿中...",
    }

    def step_callback(agent_output, **kwargs):
        """CrewAI 每步回调，更新进度文案"""
        role = ""
        try:
            role = getattr(agent_output, "role", "") or str(agent_output)[:50]
        except Exception:
            role = str(agent_output)[:50]
        for key, label in stage_labels.items():
            if key in str(role) or key in str(agent_output):
                status_box.write(label)
                break

    progress.progress(0.1, text="启动 Crew 中...")

    try:
        crew = build_crew(topic)
        try:
            result = crew.kickoff(step_callback=step_callback)
        except TypeError:
            result = crew.kickoff()

        progress.progress(0.9, text="报告生成完成，保存中...")

        report = str(result)

        # 保存到文件
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{_slugify(topic)}-{timestamp}.md"
        filepath = OUTPUT_DIR / filename
        filepath.write_text(report, encoding="utf-8")

        st.success(f"✅ 报告已生成：`{filepath}`")

        # 发布到微信公众号
        if publish_to_wechat:
            progress.progress(0.95, text="📮 正在发布到微信公众号...")
            try:
                from publish import publish_report

                pub_result = publish_report(filepath, topic=topic)
                if pub_result["success"]:
                    st.success(
                        f"📮 微信草稿已创建！标题：{pub_result['title']}\n\n"
                        f"请登录公众号后台查看并发布。"
                    )
                    # 显示封面图预览
                    cover_path = pub_result.get("cover_path", "")
                    if cover_path:
                        st.image(cover_path, caption="封面图预览", width=400)
                else:
                    st.warning(f"⚠️ 微信发布未成功：{pub_result['error']}")
            except Exception as e:
                st.warning(f"⚠️ 微信发布异常：{e}")

        progress.progress(1.0, text="完成！")

        st.markdown("---")
        st.markdown("## 📄 研究报告")
        st.markdown(report)

        st.download_button(
            label="📥 下载 Markdown",
            data=report,
            file_name=filename,
            mime="text/markdown",
        )
    except Exception as e:
        progress.empty()
        st.error(f"运行失败：{e}")
        with st.expander("查看错误详情"):
            import traceback

            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
