# AI 研究助理 Agent 🐴

多智能体协作出研究报告：**研究员**查资料 → **写作**起草 → **事实核查员**验证 → **编辑**润色，最终输出 Markdown 报告。

基于 CrewAI 编排，支持 DeepSeek / OpenAI / Moonshot / 通义千问等任何 OpenAI 兼容 API。

## 快速开始

```bash
# 1. 进入项目
cd ai-research-agent

# 2. 创建并激活 conda 环境（crewai 要求 Python >=3.10,<3.14）
conda create -n ai-research python=3.12 -y
conda activate ai-research

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API key
cp .env.example .env
# 编辑 .env 填入你的 API key（默认 DeepSeek，便宜好用）

# 5. 运行
python main.py "AI Agent 的最新发展趋势"
```

报告会输出到 `output/` 目录，文件名格式 `<主题>-<时间戳>.md`。

## 浏览器 UI（可选）

```bash
conda activate ai-research
streamlit run app.py
```

浏览器会自动打开可视化界面，可以：
- 输入研究主题或点击示例
- 实时看到四个 agent 的工作进度
- 报告生成后在页面内直接预览
- 一键下载 Markdown 报告
- 侧边栏查看历史报告

## 配置说明

编辑 `.env`：

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_PROVIDER` | deepseek | LiteLLM provider 前缀 |
| `LLM_MODEL` | deepseek-chat | 模型名 |
| `LLM_API_KEY` | (必填) | API key |
| `LLM_BASE_URL` | https://api.deepseek.com/v1 | OpenAI 兼容 endpoint |
| `TAVILY_API_KEY` | (可选) | 搜索后端，见下方说明 |
| `SEARCH_MAX_RESULTS` | 5 | 每次搜索返回结果数 |

### 搜索后端（国内已适配）

搜索优先级自动选择，国内默认用 **Bing 中国**（免费免 key）：

1. **Tavily**（配了 `TAVILY_API_KEY` 才用）— 质量最高，免费 1000 次/月，注册：tavily.com
2. **Bing 中国**（默认）— 免费、免 key、国内可用，爬取 cn.bing.com
3. **DuckDuckGo**（兜底）— 国内通常被墙，仅在 Bing 失败时尝试

> 国内用户建议配 `TAVILY_API_KEY` 获得更稳定的搜索质量，不配也能用 Bing 跑通。

### 切换到其他模型

**DeepSeek**（默认，便宜）：
```
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
```

**OpenAI**：
```
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.openai.com/v1
```

**通义千问**：
```
LLM_PROVIDER=openai
LLM_MODEL=qwen-plus
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

**Moonshot（Kimi）**：
```
LLM_PROVIDER=openai
LLM_MODEL=moonshot-v1-8k
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.moonshot.cn/v1
```

## 架构

```
ai-research-agent/
├── config.py              # 配置 + LLM 工厂
├── tools/
│   ├── __init__.py
│   └── search.py          # Web Search 工具（Tavily/Bing/DDG 三后端）
├── agents/
│   ├── __init__.py
│   ├── researcher.py      # 资深研究员（带搜索）
│   ├── writer.py          # 报告写作
│   ├── fact_checker.py    # 事实核查员（带搜索）
│   └── editor.py          # 终稿编辑
├── crew.py                # CrewAI 编排（动态注入当前日期）
├── main.py                # CLI 入口
├── app.py                 # Streamlit 可视化界面
├── .env.example           # 环境变量模板
└── output/                # 报告输出目录
```

## 工作流程

```
用户输入主题
   ↓
[研究员] 调用 web_search 多次，收集资料 → 输出研究笔记
   ↓
[写作] 基于笔记起草结构化报告 → 输出初稿
   ↓
[事实核查员] 检查初稿中每个关键论点，标注存疑处 → 输出核查报告
   ↓
[编辑] 综合初稿 + 核查报告，润色输出终稿 Markdown
   ↓
output/<主题>-<时间戳>.md
```

### 时间意识机制

所有代码中**不硬编码任何具体年份**，而是通过 `datetime.now()` 动态获取当前日期：

- **crew.py**：运行时获取当前日期和年份，注入到每个 task 描述中，引导 agent 区分「当前年份」与「上一年及之前」的数据
- **agents/*.py**：backstory 中使用「当前年份」「上一年」等相对表述，不写死具体年份
- **app.py**：Streamlit 界面的示例主题使用 `datetime.now().year` 动态生成

这样无论何时运行项目，agent 都能正确感知当前时间，搜索最新的资料，并准确标注数据的时效性。

## 副业变现思路

- 接行业研究报告定制单（电商、新媒体、SaaS 赛道）
- 做成 SaaS：用户输入主题，付费出报告
- 批量生成公众号/小红书选题调研
- 简历项目（多智能体编排 + 工具调用是当前最热方向）
