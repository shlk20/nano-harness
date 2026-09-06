# nano-harness

一个用 Python 写的最小化编码智能体（coding agent）框架，作者边阅读 Claude Code 源码边开发。它把 agentic 循环的核心——*模型调用工具，我们执行，把结果回传，再循环*——压缩进一个可读的源文件，不依赖任何框架。

## 它能做什么

给它一个任务，它会像一个小型编码智能体一样工作：

- 模型通过唯一的 `bash` 工具决定要执行哪些 shell 命令。
- 命令在项目目录里本地执行。
- 输出流回给模型，模型继续行动，直到它认为自己完成了。

这个循环是所有智能体框架的心脏，本项目的目的就是让它足够简单，看得清、改得动、能从头重建。

## 特性

- **单一工具，零抽象**：只有 `bash`。模型只看到一个工具定义，工具执行就是[src/agent.py](src/agent.py) 里的一个函数。
- **最小防护**，让你学习实验时更安全：
  - 危险命令黑名单（`rm -rf /`、`sudo`、`shutdown`……）
  - 单条命令 120 秒超时
  - 回传给模型的输出截断在 50 KB
- **交互式 REPL**（`s01 >>`）：输入问题，实时观察每次工具调用，`q` 退出。
- **兼容各类厂商**：通过 `ANTHROPIC_BASE_URL` 可对接 Anthropic 或任何 Anthropic 兼容的提供方（MiniMax、GLM、Kimi、DeepSeek……）。
- **macOS 中文输入修复**：libedit/readline 绑定，保证终端里 CJK 输入正常。

## 环境要求

- Python 3.9+
- Anthropic API key，或 Anthropic 兼容提供方的接口地址

## 安装

```bash
git clone <repo-url>
cd nano-harness
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # 然后填入你的 API key 和模型
```

环境变量（提供方列表见 [.env.example](.env.example)）：

| 变量 | 必填 | 含义 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | 是 | API key |
| `MODEL_ID` | 是 | 运行 agent 循环所用的模型 |
| `ANTHROPIC_BASE_URL` | 否 | 覆盖接口地址，用于 Anthropic 兼容提供方 |

## 使用

```bash
python src/agent.py
```

示例会话：

```
s01 >> 修复 tests/test_math.py 里失败的测试

$ pytest tests/test_math.py -x    # 工具调用以黄色打印
...
s01 >> q
```

## 工作原理

整个思路装进一个循环就够了（[src/agent.py:57](src/agent.py#L57)）：

```
while True:
    response = client.messages.create(model, system, messages, tools)
    把 response 追加进历史
    if response.stop_reason != "tool_use":
        return                 # 模型完成了
    for 每个 tool_use 块:
        output = run_bash(command)
    把 tool_result 块追加进历史    # 循环继续
```

Claude Code 的 agent 循环建立在同一个模式上——差别在于本项目把其余一切都剥掉了。系统提示词只有一行，工具 schema 是手写的 JSON，没有规划、会话管理、沙箱这些层。这正是目的：每一个特性都可以在对照真实实现学习之后，有意识地、一次一个地加回来。

## 目录结构

```
src/agent.py        整个框架：工具、执行、agent 循环、REPL
.env.example        配置模板，附 Anthropic 兼容提供方清单
requirements.txt    anthropic、python-dotenv、pyyaml
```

## 目的与路线

这是学习项目：作者阅读 Claude Code 源码的各个部分，然后在本仓库里重新实现——小而诚实，每一步只讲一个概念（`s01`、`s02`……）。计划中的演进方向：

- 更多工具（文件读写、glob、grep）
- 多轮对话持久化
- 流式响应
- 权限提示与确认流程
- hooks 与子代理

如果你是因为别的原因读到这个仓库：欢迎贡献，但请保持"文件少、每步只讲一个概念"的原则。

## 安全说明

这是教学用框架，不是生产软件。模型会在你的机器上执行任意 shell 命令；黑名单只是学习便利，不是安全边界。请只在信任的环境里、对不介意被修改的代码运行它。

## License

未声明——复用前请联系作者。
