# 更新日志 (Changelog)

## [2.2.0] - 2026-02-06

### 🤖 Agent 模式

#### ✨ 新增功能

1. **Agent 模式支持**
   - 全新的 Agent 模式，支持工具调用和多轮推理
   - 流式输出支持（Server-Sent Events）
   - 与现有 Chat 模式完全独立，互不影响
   - **前端模式切换按钮**：一键切换 Chat/Agent 模式
   - **Skywork Router 流式支持**：模拟流式输出，提升用户体验

2. **MCP (Model Context Protocol) 集成**
   - 支持连接外部 MCP 服务器
   - 内置常用 MCP 工具：web_search、calculate、get_current_time
   - 可配置的 MCP 服务器 URL
   - 自动工具发现和调用
   - **支持 `_meta` 元数据配置**：`_meta` 在外层，包含 user_id、project_id、office_id 等
   - **标准 MCP 调用方式**：使用 fastmcp Client 进行连接和调用
   - **实时 JSON 验证**：配置输入时实时检查 JSON 格式，错误提示显示在标签旁

3. **自定义 Skill 系统**
   - 可扩展的技能框架
   - 内置技能：
     - `read_file`: 读取文件内容
     - `write_file`: 写入文件
     - `execute_code`: 安全的 Python 代码执行
     - `analyze_data`: 数据统计分析
   - 支持自定义技能扩展

4. **新增 API 端点**
   - `POST /api/agent/chat`: Agent 模式流式对话
   - `GET /api/agent/tools`: 获取可用工具列表
   - `POST /api/agent/configure`: 配置 Agent 设置

5. **前端 UI 增强**
   - 顶部添加 Chat/Agent 模式切换按钮
   - 实时显示流式输出内容
   - 可视化展示工具调用过程
   - 工具调用参数和结果的美化显示
   - 模式选择状态本地持久化
   - **Agent 设置界面**：用户菜单中新增 Agent 设置选项
   - **MCP Servers 配置**：支持 JSON 格式配置多个 MCP 服务器
   - **标准 MCP 配置格式**：兼容标准 mcpServers 配置格式
   - **GitHub Skill 加载**：支持从 GitHub 仓库加载自定义 Skill（UI 已完成）

#### 🔧 技术实现

1. **新增服务模块**
   - `agent_service.py`: Agent 核心逻辑，支持流式输出和工具调用
   - `mcp_client.py`: MCP 协议客户端实现
   - `skill_manager.py`: 技能管理系统

2. **数据模型扩展**
   - `AgentConfig`: Agent 配置模型
   - `AgentRequest`: Agent 请求模型
   - 支持配置 MCP 和 Skill 的启用状态
   - TypeScript 类型定义：`ChatMode`, `AgentStreamEvent`, `ToolCall`

3. **前端服务模块**
   - `agentConfig.ts`: 管理 Chat/Agent 模式状态
   - `api.ts`: 新增 `sendAgentMessage` 流式 API 调用
   - 支持 SSE 流式数据解析

4. **依赖更新**
   - 添加 `httpx`: 用于 MCP 客户端
   - 添加 `pytz`: 用于时区支持

#### 📝 使用说明

**Agent 模式特性：**
- 支持多轮工具调用和推理
- 实时流式输出思考过程
- 可配置最大迭代次数（防止无限循环）
- 工具调用日志和结果展示

**流式输出格式：**
```json
{"type": "text", "content": "..."}
{"type": "tool_call", "tool": "...", "args": {...}}
{"type": "tool_result", "tool": "...", "result": "..."}
{"type": "thinking", "content": "..."}
{"type": "error", "content": "..."}
{"type": "done"}
{"type": "metadata", "conversation_id": "...", "tool_calls_count": 0}
```

**配置示例：**
```python
{
  "enable_mcp": true,
  "enable_skills": true,
  "mcp_server_url": "http://localhost:3000",
  "max_iterations": 10
}
```

---

## [2.1.0] - 2026-02-06

### ✨ 新增功能

1. **新增 Skywork Router 平台支持**
   - 添加 Skywork Router 作为可选的 LLM 提供商
   - 内置默认配置：base_url 和默认模型 `gpt-4.1`
   - 支持通过网页界面直接配置和使用
   - 图标：🚀

---

## [2.0.0] - 2026-02-05

### 🎉 重大更新

#### ✨ 新增功能

1. **可视化模型配置界面**
   - 新增用户菜单和头像按钮（右上角）
   - 新增模型设置弹框，支持添加、删除、切换多个 AI 模型
   - 支持的平台：GPT、Gemini、Kimi、QWen、DeepSeek、Claude、豆包等
   - 配置自动保存在浏览器 localStorage
   - 互斥的单选模型机制，一键切换默认模型

2. **智能 UI 引导**
   - 未选中模型的呼吸动画，提示用户可以点击
   - 悬停提示"点击选择"，增强可发现性
   - 选中/未选中模型的视觉对比（金色高亮 vs 置灰）
   - 文字标签"选择"/"默认"，清晰表达状态
   - 顶部指导文字，帮助新用户理解操作

3. **可爱风格 UI**
   - 二次元风格背景和渐变色
   - 自定义鼠标效果（可爱图标 + 粉色光晕 + 旋转动画）
   - 可爱的头像按钮（眨眼动画 + 装饰元素）
   - 自定义确认对话框（替代原生 window.confirm）
   - 流畅的过渡动画和悬停效果

4. **布局优化**
   - 修复页面滚动条问题，完美铺满视口
   - 优化 flex 布局，确保内容正确适配
   - 聊天窗口内部滚动，外层固定高度

#### 🔧 技术改进

1. **后端架构重构**
   - `LLMService` 支持动态模型配置，不再强制要求环境变量
   - 新增 `PLATFORM_CONFIG` 统一管理各平台的 base_url 和默认模型
   - 优化上下文构建逻辑，分离 Gemini 和 OpenAI 兼容 API 的处理
   - 改进错误处理和日志输出

2. **API 增强**
   - `ChatRequest` 新增 `llm_config` 字段（重命名自 `model_config`，避免 Pydantic 冲突）
   - 支持前端传递自定义模型配置
   - 配置优先级：前端配置 > 环境变量

3. **前端服务层**
   - 新增 `modelConfig.ts` 服务，管理 localStorage 中的模型配置
   - 支持添加、删除、启用/禁用、设置默认模型
   - 自动序列化和反序列化

4. **测试覆盖率提升**
   - 整合和优化后端测试文件
   - 新增 `conftest.py` 统一管理 pytest fixtures
   - 新增 `test_llm_service.py` 全面测试 LLM 服务
   - 测试覆盖率从 50% 提升到 83%+
   - 新增 `run_tests.sh` 脚本，方便运行测试

#### 🐛 Bug 修复

1. 修复用户菜单和模态框 z-index 过低，无法显示的问题
2. 修复鼠标粒子效果导致的性能卡顿问题
3. 修复页面出现外层滚动条的问题
4. 修复 Pydantic v2 `model_config` 字段名冲突
5. 修复测试文件中的 `KeyError: 'processed_length'`
6. 修复后端启动时强制要求 `.env` 文件的问题

#### 📚 文档更新

1. 全面更新 `README.md`
   - 新增可视化模型配置指南
   - 新增详细的使用指南（配置模型、开始对话、上传文件等）
   - 新增技术栈和项目结构说明
   - 新增常见问题解答（模型配置、后端、前端、样式问题）
   - 新增项目亮点和适用场景说明

2. 更新 `backend/env.example`
   - 标注环境变量为可选
   - 推荐使用网页界面配置

3. 新增 `backend/tests/README.md`
   - 测试运行指南

4. 新增 `CHANGELOG.md`（本文件）
   - 记录所有更新内容

#### 🗑️ 清理

删除以下冗余文件：
- `chatbot-system/docs/用户菜单和模型设置功能说明.md`
- `chatbot-system/QUICK_START_USER_MENU.md`
- `chatbot-system/MODEL_CONFIG_GUIDE.md`
- `chatbot-system/MODEL_CONFIGURATION.md`
- `backend/tests/test_context.py`（整合到 `test_llm_service.py`）
- `backend/tests/test_deepseek.py`（整合到 `test_llm_service.py`）
- `backend/tests/test_gemini_context.py`（整合到 `test_llm_service.py`）
- `backend/tests/test_gemini.py`（整合到 `test_llm_service.py`）
- `backend/tests/test_file_processing.py`（整合到 `test_file_service.py`）

---

## [1.0.0] - 2024-01-XX

### 初始版本

#### 核心功能
- 多轮对话支持
- 文件上传和智能处理（txt, md, pdf）
- 对话历史管理
- 支持多个 LLM 提供商（Gemini、OpenAI、DeepSeek、Kimi、QWen）
- 基础 UI 界面
- 测试覆盖率 >50%

---

## 版本说明

- **主版本号**（Major）：重大功能更新或架构变更
- **次版本号**（Minor）：新增功能或重要改进
- **修订号**（Patch）：Bug 修复和小优化

## 未来计划

### v2.1.0（计划中）
- [ ] 支持流式响应（SSE）
- [ ] 支持对话导出（Markdown、JSON）
- [ ] 支持主题切换（浅色/深色模式）
- [ ] 支持快捷键操作

### v2.2.0（计划中）
- [ ] 支持图片上传和识别
- [ ] 支持语音输入
- [ ] 支持代码高亮和复制
- [ ] 支持 LaTeX 公式渲染

### v3.0.0（远期规划）
- [ ] 多用户支持和权限管理
- [ ] 云端同步（可选）
- [ ] 插件系统
- [ ] 移动端适配

---

**最后更新**: 2026-02-05  
**维护者**: Skywork Team
