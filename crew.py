"""CrewAI 编排 - 定义四个 agent 的任务和执行流程"""
from datetime import datetime

from crewai import Crew, Process, Task

from agents import (
    create_editor,
    create_fact_checker,
    create_researcher,
    create_writer,
)


def build_crew(topic: str) -> Crew:
    """构建研究助理 Crew：研究员→写作→事实核查→编辑"""
    researcher = create_researcher()
    writer = create_writer()
    fact_checker = create_fact_checker()
    editor = create_editor()

    # 获取真实当前日期，硬塞进所有 task 描述
    now = datetime.now()
    today_str = now.strftime("%Y年%m月%d日")
    current_year = now.year
    prev_year = current_year - 1

    # 任务 1：研究员收集资料
    research_task = Task(
        description=(
            f"今天是 {today_str}（当前年份：{current_year} 年）。\n"
            f"围绕主题「{topic}」进行全面的研究。要求：\n"
            "1. 把主题拆成 3-5 个核心子问题，分别用 web_search 工具搜索\n"
            f"2. **搜索关键词中必须包含当前年份「{current_year}」**，以获取最新数据\n"
            "3. 每个子问题至少搜索一次，关键数据可多次搜索交叉验证\n"
            "4. 收集：行业现状、关键数据、最新趋势、代表案例、各方观点\n"
            f"5. **每条信息必须标注数据年份和来源链接**——{prev_year} 年及之前的标为历史数据，"
            f"当前年份（{current_year}）的标为最新数据\n"
            "6. 整理成结构化的研究笔记\n"
            "7. 信息不足时，主动换关键词再搜，不要凭空编造\n"
            "\n"
            "输出：一份 markdown 格式的研究笔记，包含分主题的要点和数据，"
            "每条信息标注【年份: YYYY】【来源: url】。"
        ),
        agent=researcher,
        expected_output="一份 markdown 研究笔记，分主题组织，每条信息标注年份和来源链接",
    )

    # 任务 2：写作起草报告
    writing_task = Task(
        description=(
            f"今天是 {today_str}（当前年份：{current_year} 年）。\n"
            f"基于研究员的笔记，起草关于「{topic}」的研究报告初稿。要求：\n"
            "1. 结构：摘要 → 背景与现状 → 关键数据 → 趋势分析 → 案例与代表观点 → 结论与展望\n"
            "2. 用 markdown 标题分章节（## 二级、### 三级）\n"
            "3. 关键数据用引用块或列表突出\n"
            "4. 所有论断引用研究员笔记中的来源，不自行编造数据\n"
            "5. 语言专业、客观，避免营销腔\n"
            "6. 摘要部分 200 字内概括核心结论\n"
            "7. **时间表述规范**：\n"
            f"   - 报告时间基准：{today_str}\n"
            f"   - {prev_year} 年及之前的数据明确标注为「历史数据」或「截至XXXX年」\n"
            f"   - {current_year} 年的数据作为「最新趋势」呈现\n"
            "   - 如果某条信息没有标注年份，在报告中明确说明「数据年份未标注」\n"
            "\n"
            "输出：一份结构完整的 markdown 报告初稿。"
        ),
        agent=writer,
        expected_output="一份结构完整的 markdown 报告初稿，章节清晰、论据有来源、时间标注规范",
        context=[research_task],
    )

    # 任务 3：事实核查
    fact_check_task = Task(
        description=(
            f"今天是 {today_str}（当前年份：{current_year} 年）。\n"
            "对报告初稿进行事实核查。要求：\n"
            "1. 提取初稿中所有关键论断和数据（尤其是数字、时间、事件、引用）\n"
            "2. 逐条判断：来源是否可靠、数据是否最新、逻辑是否成立\n"
            "3. 对存疑的论断调用 web_search 再次验证\n"
            "4. 输出核查清单，每条标注：【可信】/【存疑：理由】/【错误：正确信息】\n"
            "5. 重点核查：\n"
            "   - 数字准确性、时间线、因果关系、引用归属\n"
            f"   - **报告是否把 {prev_year} 年的数据误标为 {current_year} 年最新数据**\n"
            f"   - **报告的「生成时间」是否写成了旧年份（正确应为 {today_str}）**\n"
            "\n"
            "输出：一份 markdown 核查清单，逐条列出论断和核查结论。"
        ),
        agent=fact_checker,
        expected_output="一份 markdown 核查清单，逐条标注论断的可信度",
        context=[writing_task],
    )

    # 任务 4：编辑润色输出终稿
    editing_task = Task(
        description=(
            f"今天是 {today_str}（当前年份：{current_year} 年）。\n"
            "综合报告初稿和事实核查清单，输出最终可交付的报告。要求：\n"
            "1. 根据核查结果，修订或删除存疑/错误的论断，保留可信部分\n"
            "2. 如果删除导致内容缺失，补充新的内容（保持原意）\n"
            "3. 统一 markdown 格式，修正章节层级\n"
            "4. 优化语言流畅度，确保全文逻辑连贯\n"
            "5. 文末追加「## 信息来源」章节，列出主要参考链接\n"
            f"6. 文首追加报告标题（# 标题）和生成时间，**生成时间必须写：{today_str}**"
            "（不要用任何旧年份！）\n"
            "\n"
            "输出：一份干净的、可直接交付的 markdown 终稿。只输出报告正文，"
            "不要附加额外说明。"
        ),
        agent=editor,
        expected_output="一份可直接交付的 markdown 终稿，格式统一、来源完整、生成时间准确",
        context=[writing_task, fact_check_task],
    )

    return Crew(
        agents=[researcher, writer, fact_checker, editor],
        tasks=[research_task, writing_task, fact_check_task, editing_task],
        process=Process.sequential,
        verbose=True,
    )
