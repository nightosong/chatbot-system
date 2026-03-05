# Skill 和 Agent 集成重构文档

## 概述

本文档说明了 Agent 模式如何正确使用和执行 Skills。重构后的实现修复了以下问题：

1. **Skill 参数匹配问题**：Skill 现在接受任意 JSON 参数，由具体的 skill 实现来验证
2. **执行优先级问题**：Skill 优先于 MCP Tool 执行，避免名称冲突
3. **错误处理问题**：提供更详细的错误信息，便于调试

## 架构设计

### 1. Skill 定义和加载

#### Skill 结构
每个 Skill 必须包含：
- `SKILL.md`：Skill 的元数据和说明文档
  - 必须包含 YAML frontmatter（`name`, `description`）
  - Markdown 内容作为 instruction 传递给 skill 执行脚本
- `scripts/` 目录：
  - `run.py` 或 `main.py`：包含 `run()` 或 `main()` 函数

#### 示例 Skill 结构
```
skills/
└── academic-pptx-skill/
    ├── SKILL.md              # Skill 元数据和说明
    ├── scripts/
    │   └── run.py           # 执行脚本
    ├── references/          # 参考资料（可选）
    └── assets/              # 资源文件（可选）
```

#### SKILL.md 格式
```markdown
---
name: skill-name
description: "Skill 的描述，说明何时使用这个 skill"
---

# Skill 详细说明

这里是 skill 的详细使用说明，会作为 instruction 传递给执行脚本。
```

#### 执行脚本格式 (scripts/run.py)
```python
def run(arguments: dict, context: dict = None):
    """
    Skill 的主执行函数

    Args:
        arguments: 从 LLM tool call 传递的参数字典
        context: 执行上下文，包含：
            - skill_dir: skill 目录路径
            - instruction: SKILL.md 的内容
            - references_dir: references 目录路径
            - assets_dir: assets 目录路径

    Returns:
        任意可 JSON 序列化的结果
    """
    # Skill 实现
    return {"result": "success"}
```

### 2. SkillManager 实现

#### 核心方法

##### `load_skills_from_source(source, force_update=False)`
从 GitHub 或本地路径加载 skills：
```python
# 从 GitHub 加载
result = await skill_manager.load_skills_from_source(
    "https://github.com/user/skill-repo"
)

# 从本地路径加载
result = await skill_manager.load_skills_from_source(
    "/path/to/skills"
)
```

##### `get_tools()`
返回 skills 作为 LLM function tools：
```python
tools = skill_manager.get_tools()
# 返回格式：
# [
#   {
#     "type": "function",
#     "function": {
#       "name": "skill-name",
#       "description": "Skill 描述...",
#       "parameters": {
#         "type": "object",
#         "properties": {},  # 接受任意参数
#         "required": [],
#         "additionalProperties": true
#       }
#     }
#   }
# ]
```

##### `execute_skill(skill_name, arguments)`
在沙箱中执行 skill：
```python
result = await skill_manager.execute_skill(
    "academic-pptx",
    {
        "topic": "Machine Learning",
        "slides_count": 10
    }
)
```

#### 沙箱执行机制

Skills 在独立的 Python 子进程中执行，具有以下限制：
- **网络隔离**：禁用所有网络访问
- **资源限制**：
  - CPU 时间限制（默认 20 秒）
  - 内存限制（默认 256MB）
  - 文件大小限制（默认 8MB）
- **环境隔离**：使用 `-I` 标志启动，忽略用户环境

### 3. AgentService 集成

#### Tool 执行流程

```
LLM Tool Call
    ↓
AgentService._execute_tool()
    ↓
1. 检查是否为 Skill (skill_manager.has_skill())
    ↓ 是
    skill_manager.execute_skill()
        ↓
        在沙箱中执行 scripts/run.py
        ↓
        返回结果
    ↓ 否
2. 检查是否为 MCP Tool
    ↓ 是
    mcp_client.call_tool()
        ↓
        返回结果
    ↓ 否
3. 返回 "Tool not found" 错误
```

#### 执行优先级

**Skills 优先于 MCP Tools**，原因：
1. Skills 是明确加载的自定义能力
2. Skills 有更具体的行为定义
3. 避免与通用 MCP tools 的名称冲突

#### Capabilities Prompt

AgentService 会在 system prompt 中添加可用工具和 skills 的说明：

```
[Available MCP Tools]
These are external tools provided by MCP servers:
- **tool-name**
  Description: ...
  Parameters: {...}

[Available Skills]
These are custom execution units with specific behaviors:
- **skill-name**
  Description: ...
  Location: /path/to/skill

Note: Skills are executed in a sandboxed environment.
Pass all required parameters as specified in each skill's description.
```

### 4. 使用示例

#### 完整的 Agent + Skill 使用流程

```python
from services.skill_manager import SkillManager
from services.agent_service import AgentService

# 1. 初始化 SkillManager
skill_manager = SkillManager(
    workspace_root="/path/to/workspace",
    skills_root="/path/to/skills"
)

# 2. 加载 Skills
await skill_manager.load_skills_from_source(
    "https://github.com/user/academic-skills"
)

# 3. 初始化 AgentService
agent_service = AgentService(
    mcp_client=mcp_client,  # 可选
    skill_manager=skill_manager
)

# 4. 使用 Agent（Skills 会自动作为 tools 提供给 LLM）
async for chunk in agent_service.generate_stream(
    message="创建一个关于机器学习的学术演讲 PPT",
    model_config={
        "provider": "openai",
        "api_key": "sk-...",
        "model_name": "gpt-4",
        "base_url": "https://api.openai.com/v1"
    },
    enable_skills=True
):
    if chunk["type"] == "tool_call":
        print(f"Calling: {chunk['tool']}")
    elif chunk["type"] == "tool_result":
        print(f"Result: {chunk['result']}")
    elif chunk["type"] == "text":
        print(chunk["content"], end="")
```

#### LLM Tool Call 示例

当 LLM 决定使用 skill 时，会发起 tool call：

```json
{
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "function": {
        "name": "academic-pptx",
        "arguments": "{\"topic\": \"Machine Learning\", \"slides_count\": 10}"
      }
    }
  ]
}
```

AgentService 会：
1. 解析参数：`{"topic": "Machine Learning", "slides_count": 10}`
2. 调用 `skill_manager.execute_skill("academic-pptx", {...})`
3. 返回结果给 LLM 继续对话

### 5. 错误处理

#### Skill 执行失败

如果 skill 执行失败，会返回详细错误：

```python
{
    "error": "Skill 'academic-pptx' execution failed: ...",
    "skill": "academic-pptx",
    "type": "skill_error"
}
```

#### Tool 未找到

如果 tool 既不是 skill 也不是 MCP tool：

```python
{
    "error": "Tool 'unknown-tool' not found in skills or MCP tools",
    "tool_name": "unknown-tool",
    "available_skills": ["academic-pptx", "other-skill"]
}
```

#### Skill 沙箱超时

如果 skill 执行超时：

```python
{
    "success": false,
    "error": "Dynamic skill timed out after 20s",
    "skill": "academic-pptx"
}
```

## 最佳实践

### Skill 开发

1. **明确的参数定义**：在 SKILL.md 中清楚说明需要哪些参数
2. **参数验证**：在 `run()` 函数开始时验证参数
3. **错误处理**：捕获异常并返回有意义的错误信息
4. **结果结构化**：返回结构化的 JSON 对象，便于 LLM 理解

### Agent 使用

1. **优先使用 Skills**：对于复杂的、多步骤的任务，使用 skills
2. **合理设置超时**：根据 skill 的复杂度调整 `SKILL_SANDBOX_TIMEOUT`
3. **监控执行**：注意 `tool_call` 和 `tool_result` 事件
4. **处理失败**：准备处理 skill 执行失败的情况

### 系统集成

1. **分离关注点**：MCP tools 用于通用能力，Skills 用于特定领域
2. **命名规范**：使用清晰的、描述性的 skill 名称，避免与 MCP tools 冲突
3. **版本管理**：Skills 可以通过 Git 进行版本控制
4. **测试**：为每个 skill 编写单元测试

## 环境变量配置

```bash
# Skill 沙箱超时（秒）
SKILL_SANDBOX_TIMEOUT=20

# Skill Python 可执行文件
SKILL_PYTHON_EXECUTABLE=python3

# Skill 沙箱内存限制（MB）
SKILL_SANDBOX_MEM_MB=256

# Skill 沙箱文件大小限制（MB）
SKILL_SANDBOX_FSIZE_MB=8
```

## 总结

重构后的实现提供了：

1. ✅ **清晰的执行模型**：Skills 和 MCP Tools 明确分离
2. ✅ **灵活的参数传递**：Skills 可以接受任意参数结构
3. ✅ **安全的沙箱执行**：资源和网络隔离
4. ✅ **详细的错误信息**：便于调试和问题排查
5. ✅ **优雅的降级处理**：执行失败时提供有意义的反馈

这个设计使得 Agent 可以轻松地集成和使用自定义 Skills，同时保持系统的安全性和可维护性。
