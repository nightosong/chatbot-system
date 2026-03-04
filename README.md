# 🤖 AI Chat System

一个功能完整的 AI 对话系统，支持多轮对话、文件上传、对话历史管理，以及**可视化模型配置界面**。

> **💻 新特性 - Code Mode**: 现在支持 Code 模式，提供文件操作、命令执行、代码搜索等开发工具！详见 [Code Mode 文档](OPENCODE_COMPLETE_GUIDE.md) 和 [快速开始](QUICKSTART.md)。

> **🤖 Agent 模式**: 支持 Agent 模式，具备工具调用、MCP 集成和自定义 Skill 能力！详见 [Agent 模式文档](AGENT_MODE.md)。

> **🎉 可视化配置**: 支持通过网页界面直接配置多个 AI 模型，无需修改配置文件！点击右上角头像 → 设置 → 模型配置即可。

> **🔑 备选方案**: 如果你更喜欢传统方式，仍然可以在 `backend/.env` 文件中配置默认 API Key。详见 [配置 API Key](#配置方式) 章节。

## ✨ 核心功能

### 💻 **Code Mode** (NEW!)
- **文件操作**：读取、写入、编辑文件，支持多种编码
- **命令执行**：在工作区执行 bash 命令，支持超时控制
- **代码搜索**：使用 glob 和 grep 快速查找文件和内容
- **权限系统**：细粒度的操作权限控制，保障安全
- **多 LLM 支持**：支持 Gemini、OpenAI、DeepSeek、Kimi、QWen、Skywork Router 等
- **实时可视化**：查看工具执行过程和结果
- **二次元 UI**：与整体风格一致的可爱界面

### 🤖 **Agent 模式**
- **工具调用**：AI 可以主动调用工具来完成复杂任务
- **流式输出**：实时查看 AI 的思考过程和工具调用结果
- **MCP 集成**：支持 Model Context Protocol，连接外部工具服务器
- **自定义 Skill**：可扩展的技能系统（文件操作、代码执行、数据分析等）
- **内置工具**：计算器、时间查询、网络搜索等常用工具
- **独立运行**：与现有 Chat 模式完全独立，互不影响

### 🎯 **可视化模型配置**
- **网页界面配置**：无需修改配置文件，直接在网页上添加和管理多个 AI 模型
- **多模型支持**：同时配置 GPT、Gemini、Skywork Router、Kimi、QWen、DeepSeek 等多个平台
- **一键切换**：点击单选按钮即可切换默认模型，其他模型自动置灰
- **本地存储**：所有配置保存在浏览器本地，安全可靠
- **智能引导**：呼吸动画、悬停提示、文字标签，新手也能轻松上手

### 🌐 **多语言回复约束** (NEW!)
- **语言选择**：支持 8 种语言（简体中文/English/日本語/한국어/Français/Deutsch/Español/自动检测）
- **智能约束**：选择语言后，AI 会严格使用该语言回复，无论输入什么语言
- **灵活切换**：可随时切换回复语言，配置实时生效

### 💬 **多轮对话**
- 自动记录最近 10 轮对话上下文
- AI 可以引用之前的对话内容
- 支持连贯的多轮对话体验

### 📁 **智能文件处理**
- 支持最大 20MB 文件上传（txt, md, pdf）
- 智能摘要：自动压缩大文件，节省 90%+ token
- 三级处理策略：小文件完整保留，大文件智能摘要

### 📜 **对话历史管理**
- 所有对话本地持久化存储
- 可随时恢复历史对话
- 支持删除不需要的对话

### 🎨 **现代化 UI**
- 可爱的二次元风格界面
- 自定义鼠标效果（可爱图标 + 粉色光晕）
- 流畅的动画和过渡效果
- 完美适配桌面和移动端

### 🔧 **多 LLM 提供商**
- 支持 Gemini、OpenAI、Skywork Router、DeepSeek、Kimi、QWen、Claude、豆包等
- 可通过网页界面或配置文件设置
- 自动处理不同平台的 API 差异

### 🧪 **高测试覆盖率**
- 后端测试覆盖率 >83%
- 完整的单元测试和集成测试
- 包含 API、服务层、文件处理等所有核心功能

## 🏗️ 项目结构

```
chatbot-system/
├── backend/                 # FastAPI 后端
│   ├── Dockerfile          # 后端 Docker 配置
│   ├── .dockerignore       # 后端 Docker 忽略文件
│   ├── main.py             # FastAPI 主应用
│   ├── services/           # 业务逻辑服务
│   │   ├── llm_service.py          # LLM 集成（支持多提供商）
│   │   ├── agent_service.py        # Agent 模式核心逻辑
│   │   ├── code_service.py         # Code 模式核心逻辑 (NEW!)
│   │   ├── permission_service.py   # 权限管理系统 (NEW!)
│   │   ├── mcp_client.py           # MCP 协议客户端
│   │   ├── skill_manager.py        # 技能管理系统
│   │   ├── file_service.py         # 文件处理（智能摘要）
│   │   └── conversation_service.py # 对话历史管理
│   ├── models/             # 数据模型（Pydantic）
│   │   └── conversation.py     # 对话和模型配置模型
│   ├── tests/              # 后端单元测试
│   │   ├── conftest.py             # pytest 共享 fixtures
│   │   ├── test_api.py             # API 端点测试
│   │   ├── test_agent.py           # Agent 模式测试
│   │   ├── test_code_tools.py      # Code 工具测试 (NEW!)
│   │   ├── test_code_api.py        # Code API 测试 (NEW!)
│   │   ├── test_llm_service.py     # LLM 服务测试
│   │   ├── test_file_service.py    # 文件服务测试
│   │   └── test_conversation_service.py # 对话服务测试
│   ├── data/               # SQLite 数据库（自动创建）
│   ├── requirements.txt    # Python 依赖
│   ├── pytest.ini          # pytest 配置
│   └── run_tests.sh        # 测试运行脚本
│
├── frontend/               # React 前端
│   ├── Dockerfile          # 前端 Docker 配置
│   ├── .dockerignore       # 前端 Docker 忽略文件
│   ├── nginx.conf          # Nginx 配置文件
│   ├── src/
│   │   ├── components/     # React 组件
│   │   │   ├── ChatWindow.tsx         # 聊天窗口
│   │   │   ├── CodeWindow.tsx         # Code 模式窗口 (NEW!)
│   │   │   ├── ConversationList.tsx   # 对话历史列表
│   │   │   ├── UserMenu.tsx           # 用户菜单（头像下拉）
│   │   │   ├── ModelSettings.tsx      # 模型配置弹框
│   │   │   ├── AgentSettings.tsx      # Agent 设置弹框
│   │   │   ├── LanguageSettings.tsx   # 语言设置弹框
│   │   │   ├── AboutDialog.tsx        # 关于对话框
│   │   │   ├── PlatformIcon.tsx       # 平台图标组件
│   │   │   ├── CursorEffect.tsx       # 自定义鼠标效果
│   │   │   └── ConfirmDialog.tsx      # 确认对话框
│   │   ├── services/       # API 客户端
│   │   │   ├── api.ts                 # API 请求封装
│   │   │   ├── modelConfig.ts         # 模型配置管理（localStorage）
│   │   │   ├── agentConfig.ts         # Agent 配置管理
│   │   │   └── languageConfig.ts      # 语言配置管理（localStorage）
│   │   ├── types.ts        # TypeScript 类型定义
│   │   ├── App.tsx         # 主应用组件
│   │   └── index.css       # 全局样式
│   ├── assets/             # 静态资源
│   │   └── home-full-bg.jpeg # 背景图片
│   └── package.json        # Node 依赖
│
├── docs/                   # 文档
│   ├── CHANGELOG.md  # 更新日志
│   └── ... (其他详细文档)
│
├── docker-compose.yml      # Docker Compose 配置（前后端分离）
├── .dockerignore          # 根目录 Docker 忽略文件
├── Makefile               # 便捷命令集合
├── start.sh               # 本地一键启动脚本
└── README.md              # 项目概览（本文件）
```

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI 0.104.1（高性能异步 Web 框架）
- **LLM 集成**: 
  - Google Generative AI (Gemini)
  - OpenAI SDK（兼容 OpenAI、DeepSeek、Kimi、QWen 等）
- **数据库**: SQLite（轻量级本地存储）
- **文件处理**: PyPDF2（PDF 解析）
- **测试**: pytest + pytest-asyncio + pytest-cov
- **类型检查**: Pydantic v2（数据验证和序列化）

### 前端
- **框架**: React 18 + TypeScript
- **HTTP 客户端**: Axios
- **样式**: 纯 CSS（二次元风格，自定义动画）
- **状态管理**: React Hooks (useState, useEffect, useRef)
- **本地存储**: localStorage（模型配置持久化）
- **构建工具**: Create React App

### 开发工具
- **Python**: 3.8 - 3.13（推荐 3.11 或 3.12）
- **Node.js**: 14+（推荐 18.x 或 20.x LTS）
- **包管理**: pip + npm
- **版本控制**: Git
- **API 文档**: Swagger UI（自动生成）

## 🚀 Quick Start

### 方式一：Docker 启动（推荐）

**最简单的方式，一键启动！前后端自动分离部署。**

#### Prerequisites
- **Docker** (20.10+)
- **Docker Compose** (1.29+)

#### 启动步骤

1. **克隆仓库**
```bash
git clone <repository-url>
cd chatbot-system
```

2. **（可选）配置 API Key**

如果需要使用 `.env` 配置：
```bash
cd backend
cp env.example .env
# 编辑 .env 文件，配置你的 API Key
cd ..
```

> 💡 也可以跳过此步骤，启动后在网页界面配置模型。

3. **启动服务**
```bash
# 使用 docker-compose
docker-compose up -d

# 或使用 Makefile（更方便）
make up
```

4. **访问应用**
- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs
- Agent 模式文档：[AGENT_MODE.md](AGENT_MODE.md)

5. **查看日志**
```bash
# 查看所有日志
docker-compose logs -f

# 仅查看后端日志
docker-compose logs -f backend

# 仅查看前端日志
docker-compose logs -f frontend

# 使用 Makefile
make logs           # 所有日志
make logs-backend   # 后端日志
make logs-frontend  # 前端日志
```

6. **停止服务**
```bash
docker-compose down
# 或
make down
```

#### 服务架构

Docker Compose 会启动两个独立的容器：
- **backend**: FastAPI 后端服务 (端口 8000)
- **frontend**: Nginx 静态文件服务器 (端口 3000)

两个服务通过内部网络 `chatbot-network` 通信。

---

### 方式二：本地开发启动

#### Prerequisites

- **Python 3.8 - 3.13** (⚠️ Python 3.14 not yet supported - use 3.11 or 3.12 recommended)
- **Node.js 14+** (18.x or 20.x LTS recommended)
- **npm or yarn**

> **Note:** If you have Python 3.14, please use pyenv or conda to install Python 3.12. See SETUP_GUIDE.md for detailed instructions.

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd chatbot-system
```

### Step 2: Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **配置 LLM API Key:**

现在有**两种配置方式**，推荐使用方式一（网页界面配置）：

### 配置方式一：网页界面配置 (推荐 ⭐)

1. 启动应用后，点击右上角的**头像按钮**
2. 在下拉菜单中选择 **"⚙️ 设置"**
3. 点击 **"➕ 添加新模型"**
4. 填写模型信息：
   - 选择平台（GPT、Gemini、Skywork Router、Kimi、QWen、DeepSeek 等）
   - 输入模型名称（如 `gpt-4`、`gemini-2.5-flash`）
   - 输入你的 API Key
5. 点击**单选按钮**选择默认模型
6. 开始聊天！

**优点**：
- ✅ 无需修改配置文件
- ✅ 可以配置多个模型并快速切换
- ✅ 配置保存在浏览器本地，更安全
- ✅ 可视化界面，操作更直观

### 配置方式二：环境变量配置（传统方式）

如果你更喜欢传统方式，可以创建 `.env` 配置文件：

```bash
cd backend
cp env.example .env
```

然后编辑 `backend/.env` 文件，选择以下任一提供商进行配置：

#### 方式一：使用 Gemini（推荐 - 免费额度）

```env
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_api_key_here
```

**获取 API Key**: https://makersuite.google.com/app/apikey

---

#### 方式二：使用 DeepSeek（推荐 - 中文友好，性价比高）

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your_deepseek_api_key_here
MODEL_NAME=deepseek-chat
```

**获取 API Key**: https://platform.deepseek.com

**详细配置步骤**:
1. 访问 DeepSeek 平台并注册账号
2. 进入 API Keys 页面创建新密钥
3. 复制 API Key (格式: `sk-xxxxxxxx`)
4. 粘贴到 `backend/.env` 文件的 `LLM_API_KEY=` 后面
5. 保存文件

**完整配置示例** (`backend/.env` 文件内容):
```env
LLM_PROVIDER=deepseek
LLM_API_KEY=your_deepseek_api_key_here
MODEL_NAME=deepseek-chat
```

📖 更多 DeepSeek 配置详情见: [DEEPSEEK_SETUP.md](DEEPSEEK_SETUP.md)

---

#### 方式三：使用 OpenAI

```env
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key_here
MODEL_NAME=gpt-3.5-turbo
```

**获取 API Key**: https://platform.openai.com/api-keys

---

#### 方式四：使用 Kimi

```env
LLM_PROVIDER=kimi
LLM_API_KEY=your_kimi_api_key_here
MODEL_NAME=moonshot-v1-8k
```

---

#### 方式五：使用 Qwen

```env
LLM_PROVIDER=qwen
LLM_API_KEY=your_qwen_api_key_here
MODEL_NAME=qwen-turbo
```

---

**⚡ 配置位置总结**:
- 配置文件路径: `chatbot-system/backend/.env`
- 不要修改 `env.example`，只修改 `.env`
- `.env` 文件不会被提交到 Git（已在 .gitignore 中）

5. **Run backend server:**
```bash
python main.py
```

Backend will run on `http://localhost:8000`

### Step 3: Frontend Setup

1. **Open a new terminal and navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm start
```

Frontend will run on `http://localhost:3000`

### Step 4: Access the Application

Open your browser and navigate to `http://localhost:3000`

### Step 5: 配置你的第一个模型 🎉

1. 点击右上角的**可爱头像**（有眨眼动画）
2. 选择 **"⚙️ 设置"**
3. 点击 **"➕ 添加新模型"**
4. 填写信息并点击**添加**
5. 点击**单选按钮**选择该模型为默认
6. 关闭设置，开始聊天！

**🎯 推荐配置**：
- **新手推荐**：Gemini（免费额度大，申请简单）
- **中文友好**：DeepSeek 或 QWen（中文理解更好）
- **高级用户**：GPT-4（效果最好，但需付费）

## 🧪 Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
pytest
```

To see coverage report:
```bash
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Frontend Tests

```bash
cd frontend
npm test
```

To see coverage report:
```bash
npm run test:coverage
```

## 📖 使用指南

### ⚙️ 模型设置

点击右上角**头像** → **模型设置**，即可配置多个 AI 模型：

1. **添加模型**：点击 **"➕ 添加新模型"**，选择平台（GPT/Gemini/Skywork Router/Kimi/QWen/DeepSeek/Claude/豆包），输入模型名称和 API Key
2. **选择默认**：点击模型旁的**单选按钮**（✓）设为默认，只能选择一个
3. **删除模型**：点击 ✕ 按钮删除不需要的模型

> 💡 配置自动保存在浏览器本地，无需修改配置文件。

### 🌐 语言设置

点击右上角**头像** → **语言设置**，选择 AI 回复语言：

- **自动检测**：根据输入语言智能回复
- **简体中文/English/日本語/한국어** 等：固定使用指定语言回复

> 💡 语言设置会约束 AI 的回复语言，但不影响输入。

### 💬 开始对话

1. 点击顶部的 **"✨ 新对话"** 按钮
2. 在输入框中输入你的消息
3. 按 **"发送"** 或按 **Enter** 键
4. AI 会根据上下文智能回复

### 📁 上传文件

1. 点击 **"📎 上传文件"** 按钮
2. 选择文件（支持 .txt、.md、.pdf 格式）
3. 文件内容会附加到你的下一条消息中
4. 向 AI 提问关于文件的内容
5. 最大文件大小：20MB

### 📜 查看对话历史

1. 点击顶部的 **"📜 历史"** 按钮
2. 浏览你的所有历史对话
3. 点击任意对话可以恢复继续
4. 点击 🗑️ 图标可以删除对话（会弹出可爱的确认弹框）

### 🔄 多轮对话

- 系统自动维护对话上下文
- 每次回复都会考虑之前的消息
- 最多包含最近 10 轮对话的上下文
- 开始新对话可以重置上下文

### 🎯 界面特色

- **可爱的鼠标效果**：移动鼠标会显示粉色光晕和旋转的星星图标
- **呼吸动画**：未选中的模型按钮会有轻微的呼吸效果，提示你可以点击
- **悬停提示**：鼠标悬停在按钮上会显示操作提示
- **流畅动画**：所有交互都有流畅的过渡效果

## 🔧 高级配置

### 模型配置优先级

系统支持两种配置方式，优先级如下：

1. **网页界面配置**（优先级最高）
   - 通过右上角头像 → 设置 → 模型配置添加的模型
   - 保存在浏览器 localStorage 中
   - 每次聊天时优先使用选中的默认模型

2. **环境变量配置**（备选方案）
   - 通过 `backend/.env` 文件配置
   - 仅在没有网页配置时使用
   - 适合服务器部署或团队共享配置

### 后端配置

在 `backend/.env` 文件中配置（可选）：

- `LLM_PROVIDER`: 选择 LLM 提供商（gemini, openai, deepseek, kimi, qwen）
- `LLM_API_KEY`: 对应提供商的 API Key
- `MODEL_NAME`: 具体的模型名称（OpenAI 兼容 API 需要）

### 前端配置

如需修改后端 API 地址，在 `frontend` 目录创建 `.env` 文件：

```env
REACT_APP_API_URL=http://localhost:8000
```

### 自定义样式

所有 UI 样式都在 `frontend/src/components/*.css` 中，可以自由修改：

- `App.css`: 主布局和头部样式
- `ChatWindow.css`: 聊天窗口样式
- `UserMenu.css`: 用户菜单和头像样式
- `ModelSettings.css`: 模型设置弹框样式
- `CursorEffect.css`: 自定义鼠标效果
- `ConfirmDialog.css`: 确认对话框样式

## 🎨 Features in Detail

### 1. Multi-turn Conversations
- Maintains conversation context across multiple exchanges
- Intelligently includes relevant history in each request
- Context window management to prevent token overflow

### 2. File Upload & Processing
- **Supported formats:** .txt, .md, .pdf
- **Text extraction:** Handles various encodings (UTF-8, GBK, GB2312, Latin-1)
- **PDF processing:** Extracts text from all pages with page markers
- **Long document handling:** Automatic text chunking for large files
- **Validation:** File type and size validation (max 10MB)

### 3. Conversation History
- **Persistent storage:** SQLite database for local storage
- **Conversation metadata:** Title, timestamps, message count
- **Full message history:** All messages with roles and timestamps
- **Easy navigation:** Browse and resume past conversations
- **Delete support:** Remove unwanted conversations

### 4. Modern UI/UX
- **Responsive design:** Works on desktop and mobile
- **Real-time updates:** Smooth animations and transitions
- **Loading states:** Clear feedback during processing
- **Error handling:** User-friendly error messages
- **Markdown support:** Rich text formatting in responses

## 🔒 Security & Privacy

- All data stored locally in SQLite database
- No data sent to third parties except chosen LLM provider
- API keys stored in environment variables (not in code)
- File upload validation and sanitization

## 🐛 常见问题

### 模型配置相关

**问题：** "Sorry, there was an error processing your message"
- **解决方案 1**：检查是否已在网页界面配置模型（右上角头像 → 设置）
- **解决方案 2**：确认选中的模型 API Key 是否正确
- **解决方案 3**：检查 API Key 是否有足够的配额
- **解决方案 4**：如果使用环境变量，确保 `backend/.env` 文件存在且配置正确

**问题：** 找不到模型设置入口
- **解决方案**：点击右上角的**可爱头像**（有眨眼动画），然后选择 "⚙️ 设置"

**问题：** 添加模型后不生效
- **解决方案**：确保点击了**单选按钮**（粉色圆圈）选择该模型为默认

**问题：** 想要切换模型
- **解决方案**：打开设置，点击想要使用的模型旁边的单选按钮即可

### 后端问题

**问题：** "Module not found"
- **解决方案**：确保虚拟环境已激活，运行 `pip install -r requirements.txt`

**问题：** "Gemini API error" 或类似错误
- **解决方案**：验证 API Key 是否有效，是否有可用配额

**问题：** 后端启动失败
- **解决方案 1**：检查 Python 版本（推荐 3.11 或 3.12）
- **解决方案 2**：删除 `venv` 文件夹，重新创建虚拟环境

### 前端问题

**问题：** 无法连接到后端
- **解决方案**：确保后端运行在 8000 端口（访问 http://localhost:8000/docs 测试）

**问题：** 文件上传失败
- **解决方案**：检查文件大小（<20MB）和格式（.txt、.md、.pdf）

**问题：** npm install 失败
- **解决方案**：删除 `node_modules` 和 `package-lock.json`，重新运行 `npm install`

**问题：** 页面出现滚动条，没有铺满
- **解决方案**：已修复！确保使用最新代码，页面会自动铺满视口

**问题：** 鼠标效果卡顿
- **解决方案**：已优化！使用了高性能的 CSS 动画和 requestAnimationFrame

### 样式问题

**问题：** 界面显示异常
- **解决方案 1**：清除浏览器缓存，强制刷新（Ctrl+Shift+R 或 Cmd+Shift+R）
- **解决方案 2**：检查浏览器控制台是否有 CSS 加载错误

**问题：** 自定义鼠标不显示
- **解决方案**：某些浏览器可能不支持自定义鼠标，尝试使用 Chrome 或 Edge

## 📊 测试覆盖率

项目维护了 **>83%** 的测试覆盖率（后端）：

### 后端测试覆盖率
```
Name                                  Stmts   Miss  Cover
---------------------------------------------------------
backend/main.py                         80      8    90%
backend/services/llm_service.py        120     12    90%
backend/services/file_service.py        95      8    92%
backend/services/conversation_service   85      5    94%
backend/models/conversation.py          25      2    92%
---------------------------------------------------------
TOTAL                                  405     35    91%
```

**测试内容**：
- ✅ **API 端点**：请求/响应处理、错误情况、模型配置传递
- ✅ **文件服务**：所有文件格式、验证、分块、智能摘要
- ✅ **对话服务**：CRUD 操作、历史管理、并发处理
- ✅ **LLM 服务**：多提供商集成、动态配置、上下文构建
- ✅ **模型配置**：环境变量优先级、自定义配置、错误处理

### 运行测试

**后端测试**：
```bash
cd backend
source venv/bin/activate
./run_tests.sh all  # 运行所有测试并生成覆盖率报告
```

**查看覆盖率报告**：
```bash
# 在浏览器中打开 htmlcov/index.html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 前端测试
```bash
cd frontend
npm test
npm run test:coverage  # 生成覆盖率报告
```

## 🚢 Deployment

### Docker 部署（生产环境推荐）

**前后端分离架构，独立容器部署。**

#### 使用 Docker Compose

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend

# 停止服务
docker-compose down
```

#### 使用 Makefile（更便捷）

```bash
# 查看所有命令
make help

# 启动服务
make up

# 查看日志
make logs                # 所有日志
make logs-backend        # 后端日志
make logs-frontend       # 前端日志

# 重启服务
make restart             # 全部重启
make restart-backend     # 仅重启后端
make restart-frontend    # 仅重启前端

# 重建服务
make rebuild             # 全部重建
make rebuild-backend     # 仅重建后端
make rebuild-frontend    # 仅重建前端

# 进入容器
make shell-backend       # 进入后端容器
make shell-frontend      # 进入前端容器

# 健康检查
make health

# 停止服务
make down
```

#### 持久化数据

数据库文件会自动挂载到 `./backend/data/` 目录，容器重启后数据不会丢失。

#### 自定义端口

编辑 `docker-compose.yml`：

```yaml
services:
  backend:
    ports:
      - "8080:8000"  # 将后端端口改为 8080
  frontend:
    ports:
      - "3001:3000"  # 将前端端口改为 3001
```

#### 服务架构

```
┌─────────────────────────────────────┐
│     Docker Compose Network          │
│  (chatbot-network)                  │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │   Backend    │  │  Frontend   │ │
│  │  (FastAPI)   │◄─┤   (Nginx)   │ │
│  │  Port: 8000  │  │  Port: 3000 │ │
│  └──────────────┘  └─────────────┘ │
│         │                  │        │
└─────────┼──────────────────┼────────┘
          │                  │
          ▼                  ▼
     [Database]         [Static Files]
   (volume mount)      (built in image)
```

---

### 传统部署

#### Backend Deployment
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Frontend Deployment
```bash
cd frontend
npm run build
# Serve the 'build' folder with any static file server (e.g., nginx, serve)
npx serve -s build -l 3000
```

## 📝 API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

MIT License - feel free to use this project for learning or commercial purposes.

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.
