# SpeakEasy — AI 英语口语陪练自主智能体系统

> 期末项目：面向母语为中文和西班牙语（墨西哥口音）用户的 AI 英语口语智能体，帮助用户提升美国生活与职场场景下的英语交流能力。

## 核心特性（4 大评分维度）

| 评分特性 | 在系统中的展示位置 |
|---|---|
| **🤖 Agentic Workflow** | 课中页 ReAct 工作流图 + 实时 Agent Trace 面板（💭思考→🔧工具→📋观察→💬回复），agent 自主决策何时纠音/查词/调难度/推进对话；课前自主规划学习路径；课后自主生成反馈 |
| **🔧 Function Calling** | 10 个工具通过 OpenAI function calling 调用：单词释义、美式音标、句型替换、例句拓展、L1发音评估、难度自适应、错误记录、会话反馈、课程获取、路径规划。Trace 中可查看每个工具的参数与返回 JSON |
| **📊 多模态** | 语音输入（Whisper STT）+ 语音输出（TTS）+ 课前测评雷达图（PNG导出）+ 课后数据看板（6类 Plotly 交互图表：错误分布/工具使用/难度时间线/学习时长/进步趋势/场景覆盖） |
| **📝 System Prompt Architecture** | 侧边栏"查看系统提示词"折叠区，8 分节结构化展示：IDENTITY / BOUNDARIES / LEARNER_AWARENESS / SCENARIOS / TOOLS / RULES / SAFETY / OUTPUT FORMAT，含中文/西语母语者发音迁移错误 awareness |

## 技术栈

- **Python 3.9** + **Streamlit**（前端 UI）
- **OpenAI GPT-4o**（LLM + function calling 驱动 ReAct 循环）
- **OpenAI Whisper**（语音转文字 STT）
- **OpenAI TTS**（文字转语音）
- **Plotly**（可视化图表 + PNG 导出）
- **离线降级**：MockLLM 规则大脑，无 API key 时 agentic workflow / function calling / 图表全部可用

## 快速开始

### 1. 安装依赖

```bash
cd ai-english-coach
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置 API Key（可选）

```bash
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY
# 留空则自动进入离线演示模式（MockLLM，文字对话 + 图表，无语音）
```

### 3. 启动应用

```bash
bash run.sh
# 或: streamlit run app.py
```

浏览器打开 `http://localhost:8501`，授权麦克风权限（在线模式）。

## 使用指南

### 课前阶段（能力测评）
1. 填写学习者信息（母语、年龄、职业、目标、痛点场景）
2. 完成四维度测评（听力/口语/阅读/写作）
3. 查看雷达图 + CEFR 评级 + 个性化学习路径
4. 下载测评结果图片（PNG）

### 课中阶段（语音对话训练）
1. 选择练习场景（租房/就医/面试/校园/出行/银行/餐厅/职场）
2. 录音或输入文本与 AI 教练对话
3. 观察右侧 Agent Trace 面板，了解 AI 的自主决策过程
4. 接收实时纠音、语法纠正、地道表达建议
5. 难度根据表现自动调整（CEFR 自适应）

### 课后阶段（反馈与看板）
1. 查看单次练习反馈（错误汇总、重点句型、生词、鼓励语）
2. 浏览数据看板（错误分布、工具使用、难度变化、学习时长）
3. 获取个性化学习推荐

## 在线 vs 离线模式

| 功能 | 在线模式 (有 API Key) | 离线模式 (无 API Key) |
|---|---|---|
| 语音输入 (STT) | ✅ Whisper | ❌ 文本输入 |
| 语音输出 (TTS) | ✅ OpenAI TTS | ❌ |
| LLM 对话 | ✅ GPT-4o | ✅ MockLLM 规则引擎 |
| Function Calling | ✅ GPT-4o 原生 | ✅ 模拟工具调用 |
| Agent Trace | ✅ 真实决策链 | ✅ 模拟决策链 |
| 难度自适应 | ✅ | ✅ |
| 测评雷达图 | ✅ | ✅ |
| 数据看板 | ✅ | ✅ |
| PNG 导出 | ✅ | ✅ |

## 项目结构

```
ai-english-coach/
├── app.py                  # Streamlit 入口 + 三阶段路由
├── config.py               # 全局配置 + 模式探测
├── core/
│   ├── agent.py            # ReAct 编排器（agentic 核心）
│   ├── llm_client.py       # LLM 抽象 + OpenAI + MockLLM
│   ├── speech.py           # Whisper STT + TTS
│   ├── state.py            # 数据模型 + 会话持久化
│   └── trace.py            # Agent 决策轨迹
├── prompts/
│   ├── system_prompt.py    # 8 分节系统提示词构建器
│   └── sections.py         # L1 感知错误模式
├── tools/                  # 10 个 function calling 工具
│   ├── registry.py         # 工具注册 + schema + 分发
│   ├── dictionary.py       # 单词/音标/例句
│   ├── patterns.py         # 句型替换
│   ├── pronunciation.py    # L1 发音评估
│   ├── difficulty.py       # 难度自适应
│   ├── curriculum.py       # 课程/路径规划
│   └── feedback.py         # 错误记录/会话反馈
├── assessment/             # 测评引擎 + 报告
├── visualization/          # Plotly 图表 + PNG 导出
├── data/                   # 场景库/课程库/错误模式库
├── pages/                  # 课前/课中/课后页面
├── ui/                     # 可复用组件 + 样式
└── tests/                  # 28 个单元测试
```

## 运行测试

```bash
python3 tests/test_tools.py      # 13 个工具测试
python3 tests/test_agent.py      # 9 个编排器测试
python3 tests/test_degraded.py   # 6 个离线降级测试
```

## 演示动线（30 秒展示 4 特性）

1. **系统提示词** → 侧边栏展开"System Prompt Architecture"，展示 8 分节 + L1 awareness
2. **多模态** → 课前测评生成雷达图 + 下载 PNG
3. **Agentic + Function Calling** → 课中对话，观察 Trace 面板的 💭→🔧→📋 多步链 + 工具调用卡
4. **多模态** → 课后数据看板 6 类图表

## CEFR 分级

| 级别 | 能力描述 |
|---|---|
| A1 入门 | 理解和使用日常简单表达 |
| A2 初级 | 应对日常生活基础场景对话 |
| B1 中级 | 熟练应对日常和职场基础场景 |
| B2 中高级 | 应对复杂职场和学术场景 |
| C1-C2 高级 | 接近母语水平 |
