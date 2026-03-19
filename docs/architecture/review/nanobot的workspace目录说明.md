`~/.nanobot/workspace`（或你自定义的 `~/.nanobot-runner` 作为 nanobot workspace）主要是给 Agent 用的“工作目录 + 记忆目录 + 技能目录”。下面按“典型目录/文件 + 作用 + 存放什么信息”来梳理。
---
## 1. 总体结构示意
```text
~/.nanobot/workspace/（或 ~/.nanobot-runner）
├── memory/
│   ├── MEMORY.md          # 长期记忆（事实 / 偏好 / 用户画像）
│   └── HISTORY.md         # 事件日志（可 grep 的历史摘要）
├── sessions/
│   └── {channel}_{chat_id}.jsonl  # 每个会话的原始消息历史
├── skills/
│   └── {skill_name}/
│       └── SKILL.md       # 技能说明（Prompt + 工作流）
├── HEARTBEAT.md           # 定期心跳任务（定时触发 Agent 执行任务）
├── AGENTS.md              # Agent 行为准则 / 工作流（全局）
├── SOUL.md                # 人格、价值观、语气风格
├── USER.md                # 用户画像 / 偏好 / 习惯
├── TOOLS.md               # 工具使用规范 / 约束
├── IDENTITY.md            # 身份标识（可选）
└── media/（若有）         # 接收到的图片/文件等媒体文件
```
下面分块说明。
---
## 2. 核心目录与文件
### 2.1 `memory/`：两层记忆系统
nanobot 的记忆机制主要靠两个 Markdown 文件实现：`MEMORY.md` + `HISTORY.md`。
#### `memory/MEMORY.md` —— 长期事实 / 用户画像
- **作用**：存放“对谁、在什么环境下、偏好什么、当前目标是什么”这类**长期事实**。每次对话开始时，`MEMORY.md` 的全部内容会被拼进 system prompt，让 Agent “认识”用户。
- **典型内容**：
  - 用户基本信息：姓名、地理位置、职业
  - 偏好：语言风格、输出格式（喜欢详细代码示例 / 偏好简洁）、优先级（质量优先 vs 速度优先）
  - 项目上下文：当前项目目录、技术栈、依赖约束
  - 已知的习惯：常用工具、作息时间、训练目标（对你这个跑步项目就是：VDOT、周跑量、比赛目标等）
> 对你来说，`USER.md` 可以和 `MEMORY.md` 合并，或者让 `MEMORY.md` 包含用户画像，而 `USER.md` 放更稳定的“人格/角色设定”。
#### `memory/HISTORY.md` —— 事件日志（可搜索）
- **作用**：记录“发生过什么”，是按时间追加的事件摘要。**不会**塞进 prompt，而是通过 `grep` 搜索，用来回忆过去的重要事件。
- **典型内容**：
  - 每次关键对话的简要摘要（带时间戳）
  - 重要决策记录：比如“改用某个训练计划、调整比赛目标、引入新装备”等
  - 关键问题排查：例如某次配置错误、权限问题的处理过程
---
### 2.2 `sessions/`：原始对话历史
- **文件**：`sessions/{channel}_{chat_id}.jsonl`  
  例如：`telegram_123456789.jsonl`、`feishu_abc123.jsonl`。
- **作用**：
  - 存放每个会话的原始消息列表（用户 / Assistant / 工具调用记录），**只追加，不修改**，以保持 Prompt Cache 有效。
  - Agent 的 `SessionManager` 会从这里加载历史，并根据 `last_consolidated` 决定哪些消息要发给 LLM，哪些已经被“压缩”进 `MEMORY.md` / `HISTORY.md`。
- **存放信息**：
  - 每条消息的 role、content、时间戳
  - 工具调用和返回结果
  - 指针：`last_consolidated`，标记已经整理到哪条消息。
---
### 2.3 `skills/`：技能扩展（Skill System）
nanobot 的技能系统基于 Markdown 文件：`skills/{skill_name}/SKILL.md`。
- **作用**：
  - 用自然语言描述一个“可复用的任务流程 / 能力模块”，例如“生成训练计划”、“评估伤病风险”、“写周报”等。
  - 技能可以设置为 `always: true`（每次都完整加载进 system prompt）或 `always: false`（仅摘要列出，按需读取）。
- **存放信息**：
  - 技能名称、描述
  - 使用场景、前置条件
  - 具体步骤（Prompt 模板 + 工具调用顺序）
  - 输出格式要求
> 你可以把“跑步训练计划生成”、“VDOT 预测”、“伤病风险预警”等，都做成一个个 Skill，放到 `skills/` 下，让 Agent 在需要时自动加载。
---
### 2.4 `HEARTBEAT.md`：定时任务 & 心跳
- **作用**：
  - nanobot 有一个 `HeartbeatService`，每 30 分钟唤醒一次 Agent，读取 `HEARTBEAT.md` 里的任务清单，执行未完成的任务（类似“定期任务列表”）。
- **存放信息**：
  - 待办任务列表（Markdown 任务列表 `- [ ]`）
  - 示例：
    ```markdown
    ## Periodic Tasks
    - [ ] 检查天气，如果下雨提醒我带伞
    - [ ] 检查训练计划，如果今天有长距离跑，提醒我早点休息
    - [ ] 整理 MEMORY.md，避免太冗长
    ```
- Agent 会定期读取这个文件，执行里面的任务，并通过当前活跃的渠道返回结果。
---
### 2.5 顶层 Prompt 文件：AGENTS.md / SOUL.md / USER.md 等
这些文件是 Agent 的“人格 + 行为准则 + 用户画像”的核心配置。
| 文件        | 作用                                                         | 典型内容                                                         |
|------------|--------------------------------------------------------------|------------------------------------------------------------------|
| `AGENTS.md`| Agent 的行为准则、工作流程、约束                             | 如何调用工具、优先级原则、错误处理策略等         |
| `SOUL.md`  | 人格、价值观、语气风格                                       | “你是一个专业的跑步教练，鼓励但不过度吹捧，重视科学训练……”    |
| `USER.md`  | 用户画像 / 偏好 / 习惯                                       | 用户背景、技术栈、语言偏好、训练目标等          |
| `TOOLS.md` | 工具使用规范和约束                                           | 哪些工具可以调用、权限边界、禁止操作等          |
| `IDENTITY.md` | 身份标识（可选）                                          | “我是 nanobot-runner，你的个人跑步教练助理”等                  |
这些文件会被 `ContextBuilder` 在构建 system prompt 时按优先级加载：身份 → Bootstrap 文件 → MEMORY.md → 技能摘要。
---
### 2.6 `media/`：媒体文件（飞书 / Telegram 等收到的文件）
- **作用**：
  - 当通过飞书、Telegram 等渠道发送图片、文件给机器人时，nanobot 会把它们下载到 `media/` 目录，并生成文件路径，供 Agent 使用。
- **存放信息**：
  - 图片、PDF、代码文件等二进制文件
  - 可能按渠道 / 日期再分子目录（具体结构会随版本略有不同）
---
## 3. 和你当前设计的关系
你打算：
- `~/.nanobot` 作为 nanobot 底座配置目录（`config.json` 等）。
- `~/.nanobot-runner` 作为软件自己的目录，同时作为 nanobot 的 workspace。
结合上面的结构，可以这样映射：
```text
~/.nanobot/
└── config.json            # 全局配置：providers、channels、tools 等
~/.nanobot-runner/（作为 workspace）
├── memory/
│   ├── MEMORY.md          # 跑步画像 + 长期偏好（你可用脚本从 profile.json 生成）
│   └── HISTORY.md         # 训练事件、重要决策摘要
├── sessions/
│   └── feishu_{chat_id}.jsonl  # 飞书会话历史（如果你用飞书做交互）
├── skills/
│   ├── plan/
│   │   └── SKILL.md       # “生成训练计划”技能
│   ├── injury/
│   │   └── SKILL.md       # “伤病风险预警”技能
│   └── vdot/
│       └── SKILL.md       # “VDOT 预测”技能
├── AGENTS.md              # 行为准则：如何调用工具、如何更新记忆等
├── SOUL.md                # 跑步教练人格
├── USER.md                # 你可以在这里写初始用户画像，或让程序从 profile.json 导入
├── HEARTBEAT.md           # 定时任务：如“每周一生成本周训练计划”
└── media/                 # 接收到的训练截图、GPS 数据等
```
---
## 4. 小结
- `~/.nanobot/workspace`（或你的 `~/.nanobot-runner`）是 Agent 的“办公桌”：  
  - 文件系统工具（read/write/edit）默认只在这个目录下工作（如果开启 `restrictToWorkspace`）。
  - 记忆、会话、技能、心跳任务等，都以文件形式存在这里，便于查看、调试和版本控制。
- 对你的项目来说，把 `~/.nanobot-runner` 作为 workspace 完全可行，关键是：
  - 用 `memory/MEMORY.md` 存“长期画像 + 偏好 + 目标”；
  - 用 `sessions/` 存原始对话；
  - 用 `skills/` 封装训练计划生成、预测、报告等能力；
  - 用 `HEARTBEAT.md` 做定期提醒和计划生成。
这样既符合 nanobot 的设计惯例，又能方便地扩展你自己的“跑步教练智能体”。
