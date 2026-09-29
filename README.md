# AI 研究助理 Agent 🐴

多智能体协作出研究报告：**研究员**查资料 → **写作**起草 → **事实核查员**验证 → **编辑**润色，最终输出 Markdown 报告。

基于 CrewAI 编排，支持 DeepSeek / OpenAI / Moonshot / 通义千问等任何 OpenAI 兼容 API。

支持一键发布到**微信公众号草稿箱**（自动生成封面图，不会自动发布）。

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

# 生成后自动发布到微信公众号草稿箱
python main.py --publish "AI Agent 的最新发展趋势"

# 强制不发布
python main.py --no-publish "AI Agent 的最新发展趋势"
```

报告会输出到 `output/` 目录，文件名格式 `<主题>-<时间戳>.md`。

## 微信公众号发布（可选）

报告生成后，自动完成以下流程：

```
报告 Markdown → AI 生成封面图 → Markdown 转微信兼容 HTML
    → 上传图片到微信素材库 → 创建草稿（不发布，需登录后台手动发布）
```

### 配置

在 `.env` 中填写微信公众号信息：

```bash
# 必填
WECHAT_APP_ID=wx_your_app_id
WECHAT_APP_SECRET=your_app_secret

# 可选
WECHAT_PUBLISH=true          # 是否启用（默认 true）
WECHAT_AUTO_COVER=true       # 是否自动生成封面图（默认 true）
```

### 封面图生成方式

| 方式 | 配置 | 说明 |
|---|---|---|
| `auto` | 默认 | 自动选择：优先 AI 生图，失败降级到 Pillow |
| `openai_compatible` | 需 API key | OpenAI 兼容 API（DashScope 通义万相、SiliconFlow 等） |
| `dashscope` | 需 API key | DashScope 通义万相（异步 API） |
| `pillow` | 无需 API | 本地 Pillow 生成简约渐变封面（兜底方案） |

AI 生图配置示例（以通义万相为例）：

```bash
COVER_IMAGE_PROVIDER=openai_compatible
COVER_IMAGE_API_KEY=sk-your-dashscope-key
COVER_IMAGE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
COVER_IMAGE_MODEL=wanx-v1
COVER_IMAGE_STYLE=简约、扁平设计、柔和渐变背景、干净现代
```

不配置封面图 API 时，默认使用 Pillow 本地生成纯色渐变封面，不需要任何额外 API。

### CLI 使用

```bash
# 跟随 .env 配置（默认发布）
python main.py "主题"

# 强制发布
python main.py --publish "主题"

# 强制不发布
python main.py --no-publish "主题"
```

### Streamlit UI

在 Streamlit 界面中，如果微信配置已启用，会出现「📮 生成后发布到微信公众号草稿箱」复选框，勾选后自动生成报告并推送草稿。

### 注意事项

- 微信公众号需要**认证**才能使用草稿箱 API（订阅号/服务号均可）
- 永久素材（封面图）每日上传上限：未认证 10 次，认证号 100 次
- 草稿创建后**不会自动发布**，需登录公众号后台手动发布
- IP 白名单：微信公众平台 → 开发 → 基本配置 → IP 白名单，需添加运行机器的 IP

## 浏览器 UI（可选）

```bash
conda activate ai-research
streamlit run app.py
```

浏览器会自动打开可视化界面，可以：
- 输入研究主题或点击示例
- 实时看到四个 agent 的工作进度
- 勾选是否发布到微信公众号
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
| `WECHAT_APP_ID` | (可选) | 微信公众号 AppID |
| `WECHAT_APP_SECRET` | (可选) | 微信公众号 AppSecret |
| `WECHAT_PUBLISH` | true | 是否启用微信发布 |
| `COVER_IMAGE_PROVIDER` | auto | 封面图生成方式 |
| `COVER_IMAGE_API_KEY` | (可选) | 封面图 AI 生成 API key |
| `COVER_IMAGE_BASE_URL` | (可选) | 封面图 API 地址 |

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
├── publish/               # 微信公众号发布模块
│   ├── __init__.py
│   ├── weixin.py          # 微信 API 客户端（token/素材/草稿）
│   ├── cover.py           # AI 封面图生成（OpenAI/DashScope/Pillow）
│   ├── converter.py       # Markdown → 微信 HTML 转换器
│   └── publisher.py       # 发布主流程编排
├── crew.py                # CrewAI 编排（动态注入当前日期）
├── main.py                # CLI 入口
├── app.py                 # Streamlit 可视化界面
├── .env.example           # 环境变量模板
└── output/                # 报告输出目录
    └── covers/            # 封面图输出目录
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
   ↓
[可选] 📮 微信公众号发布
   → AI 生成封面图 → MD 转微信 HTML → 上传图片 → 创建草稿
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
