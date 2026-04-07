# nanoAgent

一个基于 OpenAI Compatible Chat Completions 的多 Agent 终端实验项目。

当前实现重点不是“单 Agent 对话”，而是：

- 主 Agent + 可动态 spawn 的子 Agent
- 基于 JSONL inbox 的消息总线协作
- 函数工具调用闭环（streaming tool calls）
- 可插拔 Skill 系统
- 运行日志与会话压缩

## 当前能力

- 终端聊天室式交互（用户消息通过 message bus 投递到 mainAgent）
- 单任务内多轮工具调用，直到模型给出最终文本回复
- 子任务代理（`sub_agent_task_tool`）
- 动态创建团队成员代理（`spawn`）
- 代理间消息收发（`send_message` / `read_inbox`）
- Skill 自动发现与按需加载（读取 `skills/**/SKILL.md`）
- 对话压缩（`compact`）与转储（`.transcripts/*.jsonl`）

## 环境要求

- Python 3.11+
- 环境变量 `ARK_API_KEY`

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
export ARK_API_KEY="your_api_key"
python cmd/main.py
```

退出命令：`exit` 或 `quit`。

## 使用方式

启动后直接输入文字即可。所有消息默认发给 leader agent（`mainAgent`），由它分析语义后决定：

- 自己处理（代码编辑、shell 命令等）
- 转发给已有的在线 Agent
- spawn 一个新的专业 Agent 来处理

终端会在每次输入前显示**在线状态栏**，例如：

```
─── agents: ● mainAgent(leader)  ● reviewer(code-review)  ○ wangzai(dog) ───
>
```

- `●` 绿色 = 在线（心跳活跃）
- `○` 灰色 = 离线

示例对话：

- `帮我检查 tool_bash.py 有没有安全风险` → leader 可能 spawn 一个 reviewer 来处理
- `给 reviewer 说一下关注命令注入问题` → leader 会转发给 reviewer
- `列出当前目录的文件` → leader 自己用 bash 工具处理

## 项目结构（与当前代码一致）

- `cmd/main.py`：CLI 入口，启动 `mainAgent` 后台线程并接收用户输入
- `agent.py`：Agent 主循环、流式输出、tool call 聚合与执行
- `agent_context.py`：Agent 上下文（messages/model/client/token 配置）
- `agent_logger.py`：每次 LLM 调用步骤日志，输出到 `agent_log.json`
- `agent_profile.py`：统一构建 Agent 的 system template、工具注册表与 profile-tool 映射
- `agent_factory.py`：统一创建 Agent 实例并集中默认模型/token 参数
- `client.py`：OpenAI compatible client 初始化
- `config.py`：全局路径与配置（`.team`、`.transcripts`、`skills` 等）
- `tool.py`：Tool 抽象
- `tool_*.py`：具体工具实现
- `skills/`：Skill 仓库（示例：`skills/code-review/SKILL.md`）

## 工具清单

- `bash`：执行 shell 命令（带非常基础的危险命令拦截）
- `read_file`：读取文件
- `write_file`：写文件（覆盖写）
- `edit_file`：按字符串替换编辑文件
- `members`：读取团队成员名
- `spawn`：创建并启动新 Agent 线程
- `send_message`：向指定成员写入 inbox
- `read_inbox`：读取并清空指定成员 inbox
- `sub_agent_task_tool`：创建一次性子代理执行子任务
- `get_skill`：读取指定 skill 的正文内容
- `compact`：压缩上下文并保存 transcript

## 装配策略（已配置驱动）

- `agent_profile.py` 中维护 `BASE_TOOL_REGISTRY`（工具名 -> 工具实例）
- `PROFILE_TOOL_NAMES` 定义 profile 需要的工具名序列（`main` / `spawned` / `delegated`）
- `build_tool_box(profile, extra_registry=...)` 按映射生成最终 toolbox
- 动态工具（如 `spawn`、`sub_agent_task_tool`）通过 `extra_registry` 注入，避免循环依赖

## 核心运行机制

1. 用户在终端输入消息。
2. `cmd/main.py` 将消息写入 `mainAgent` inbox（`.team/inbox/mainAgent.jsonl`）。
3. `Agent.run_loop()` 轮询 inbox，取到消息后包装为 `<inbox>...</inbox>` 写入上下文。
4. `_stream_chat()` 调用 `chat.completions.create(stream=True, tools=...)`。
5. 若模型返回 tool calls，`handle_tool_calls()` 执行工具并将结果以 `role=tool` 回填。
6. 重复步骤 4-5，直到没有 tool calls，任务结束。

## 运行时产物

- `.team/config.json`：团队成员状态
- `.team/inbox/*.jsonl`：各 Agent 收件箱
- `.transcripts/transcript_*.jsonl`：`compact` 产出的会话归档
- `agent_log.json`：最近一次运行的结构化日志

## 已知限制

- `bash` 仅做了弱拦截，不是沙箱
- 工具路径权限和写入边界尚未严格限制
- `read_file` / `write_file` / `edit_file` 默认按当前工作目录直接访问
- inbox 轮询间隔为 3 秒，实时性一般
- 错误恢复、重试、超时分级策略较基础

## 迭代路线（建议我们按这个节奏一起推进）

### Iteration 1（稳定性）

- 加统一异常类型与错误码（tool 层 + agent 层）
- 为关键路径补最小可运行测试（工具单测 + 一个端到端冒烟）
- 加消息与工具调用 trace id，方便排障

### Iteration 2（安全与边界）

- 给文件工具加工作目录白名单和路径规范化校验
- 将 `bash` 从黑名单改成可配置 allowlist 策略
- 增加敏感命令审计日志

### Iteration 3（协作能力）

- 改进 `members`：返回结构化成员信息（名字/角色/状态）
- 增加任务状态机（queued/running/done/failed）
- 增加 agent 生命周期管理（优雅停止、超时回收）

### Iteration 4（可维护性）

- 抽离工具注册与依赖装配（避免多处重复 TOOL_BOX）
- 统一模型配置与默认参数来源（环境变量 + 配置文件）
- 给 README 增补架构图和开发者贡献流程

## 下一步怎么一起做

你可以直接告诉我：

1. `从 Iteration 1 开始，先做测试框架和首批单测`
2. `先做安全改造（文件工具路径边界 + bash allowlist）`
3. `先做架构清理（抽离工具注册）`

我会按你选的顺序直接改代码、跑验证，并持续更新文档。
