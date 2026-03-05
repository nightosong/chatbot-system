# Skill 加载和识别问题修复

## 🐛 问题描述

用户询问 Agent 能使用哪些 skills 时，Agent 回答说只有 MCP tools，没有识别到 skills。

## 🔍 根本原因

Skill 加载失败，原因是 **SkillManager 的名称验证太严格**：

```python
# skill_manager.py:597-600 (旧代码)
if name != dir_name:
    raise ValueError(
        f"name '{name}' must match parent directory name '{dir_name}'"
    )
```

### 具体问题

1. **Skill 目录名**：`academic-pptx-skill`
2. **SKILL.md 中的 name**：`academic-pptx`
3. **验证要求**：name 必须等于目录名
4. **结果**：验证失败，skill 无法加载

### 为什么会有这个问题？

- Skill name 是**逻辑标识符**，应该简洁、易用
- 目录名是**文件系统组织**，可能包含后缀（如 `-skill`）用于分类
- 强制两者相同限制了灵活性

## ✅ 修复方案

### 放宽名称验证

移除 "name 必须等于目录名" 的限制：

```python
# skill_manager.py:586-601 (新代码)
def _validate_name(self, name: str, dir_name: str):
    """Validate skill name.

    Note: We don't enforce that name must match directory name, as the skill name
    is a logical identifier while directory name is just filesystem organization.
    """
    if not name:
        raise ValueError("Missing required field: name")
    if len(name) > 64:
        raise ValueError("name must be <= 64 characters")
    if not self.NAME_PATTERN.match(name):
        raise ValueError(
            "name must contain lowercase letters/numbers and hyphens, no leading/trailing hyphen, no consecutive hyphens"
        )
    if "--" in name:
        raise ValueError("name must not contain consecutive hyphens")
    # ✅ 移除了 name == dir_name 的检查
```

### 为什么这样修复？

1. **灵活性**：允许 skill name 和目录名不同
2. **语义清晰**：skill name 用于 LLM 调用，目录名用于组织
3. **向后兼容**：不影响已有的 name == dir_name 的 skills
4. **符合实践**：实际使用中，skill name 通常比目录名简洁

## 🧪 验证修复

### 测试加载

```bash
python -c "
import asyncio
from services.skill_manager import SkillManager

async def test():
    skill_manager = SkillManager.get_instance()
    result = await skill_manager.load_skills_from_source(skill_manager.skills_root)
    print('Loaded:', result['loaded_skills'])
    print('Count:', result['loaded_count'])

asyncio.run(test())
"
```

**预期输出**：
```
Loaded: ['academic-pptx']
Count: 1
```

### 测试 Agent 识别

```python
# 检查 system prompt 是否包含 skills
agent_service = AgentService(mcp_client=None, skill_manager=skill_manager)
tools = skill_manager.get_tools()
skill_summaries = skill_manager.list_skills()
capabilities = agent_service._build_capabilities_prompt(tools, skill_summaries)

print(capabilities)
# 应该包含 [Available Skills] 部分
```

## 📊 修复影响

### 修复前
- ❌ Skills 无法加载（验证失败）
- ❌ Agent 只能看到 MCP tools
- ❌ 用户无法使用自定义 skills

### 修复后
- ✅ Skills 正常加载
- ✅ Agent 能识别和使用 skills
- ✅ System prompt 包含 skills 信息
- ✅ Skills 作为 function tools 提供给 LLM

## 🚀 部署说明

### 1. 确认修复已应用

检查 `skill_manager.py:586-601`，确认 `_validate_name` 方法不再检查 `name == dir_name`。

### 2. 重启服务

```bash
# 修复只在服务启动时生效
python main.py  # 或使用你的启动命令
```

### 3. 验证 Skills 已加载

查看启动日志：
```
INFO: Loaded local skills on startup: count=1 names=academic-pptx
```

### 4. 测试 Agent

向 Agent 询问：
```
用户：我能使用哪些技能？

Agent：我目前可以使用以下技能：

1. **academic-pptx** - 用于创建和改进学术演讲...
```

## 🎯 相关修改

### 文件变更

- `services/skill_manager.py` - 放宽名称验证 (586-601 行)

### 其他相关文件

- `services/agent_service.py` - Skills 调用逻辑（已正确）
- `prompts/general_agent.md` - Skills 使用指南（已正确）
- `main.py` - Skills 启动加载（已正确）

## 📝 最佳实践

### Skill 命名建议

**Skill Name（在 SKILL.md 中）**：
- ✅ 简洁、易记：`academic-pptx`、`code-review`、`data-analysis`
- ✅ 小写 + 连字符：符合 NAME_PATTERN
- ✅ 反映功能：让 LLM 和用户易于理解

**目录名**：
- ✅ 可以添加后缀：`academic-pptx-skill`、`code-review-v2`
- ✅ 用于组织分类：`skills/academic-pptx-skill/`、`skills/github/xxx/`
- ✅ 不影响调用：LLM 使用 skill name，不是目录名

### 示例结构

```
skills/
├── academic-pptx-skill/          # 目录名可以包含后缀
│   ├── SKILL.md                  # name: academic-pptx （不需要匹配）
│   └── scripts/
│       └── run.py
├── data-analysis-v2/             # 目录名可以包含版本
│   ├── SKILL.md                  # name: data-analysis （不需要匹配）
│   └── scripts/
│       └── run.py
└── simple-skill/                 # 如果愿意，也可以保持一致
    ├── SKILL.md                  # name: simple-skill
    └── scripts/
        └── run.py
```

## 🔄 后续优化建议

### 1. 添加 Skill 重复检测

如果两个目录定义了相同的 skill name，应该报错或警告：

```python
def _load_skills_from_path(self, source_path, source_meta):
    # ...
    for skill_file in skill_files:
        skill = self._parse_skill_file(skill_file, source_meta)

        # 检查重复
        if skill.name in self._skills:
            existing = self._skills[skill.name]
            raise ValueError(
                f"Duplicate skill name '{skill.name}': "
                f"{existing.directory} and {skill.directory}"
            )

        self._skills[skill.name] = skill
```

### 2. 添加 Skill 元数据字段

在 `list_skills()` 返回值中添加目录名：

```python
{
    "name": "academic-pptx",
    "directory_name": "academic-pptx-skill",  # 新增
    "description": "...",
    "metadata": {
        "path": "/path/to/academic-pptx-skill",
        # ...
    }
}
```

### 3. 文档更新

更新 SKILL.md 模板，说明 name 可以和目录名不同。

## ✅ 总结

问题的根本原因是 **过度严格的验证逻辑**，修复方法是 **放宽验证规则**。

**关键改变**：
- Skill name（逻辑标识）≠ 目录名（物理组织）
- 两者可以相同，但不强制要求
- 这提供了更好的灵活性和可维护性
