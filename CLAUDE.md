# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Chat System with support for three distinct operational modes. The system is built as a containerized full-stack application with separate backend (FastAPI) and frontend (React + TypeScript) services.

**Key Features:**
- Multi-turn conversations with context management
- File upload and intelligent summarization (txt, md, pdf)
- Agent mode with tool calling (MCP protocol + custom skills)
- **Code mode with OpenCode-inspired development tools** (✅ IMPLEMENTED)
- Multi-LLM provider support (Gemini, OpenAI, DeepSeek, Kimi, QWen, Claude, Skywork Router, etc.)
- Web-based model configuration (stored in localStorage)
- Multilingual response constraints
- Conversation history persistence (SQLite)
- Anime-style UI with pink gradients and glassmorphism effects

## Architecture

### Three-Mode System

The system supports **three independent modes** that run in parallel:

1. **Chat Mode** (`/api/chat`): Standard multi-turn conversations for general Q&A
2. **Agent Mode** (`/api/agent/chat`): Streaming responses with tool calling (MCP + custom skills)
3. **Code Mode** (`/api/code/chat`): OpenCode-inspired development agent with 6 core tools (read/write/edit/bash/glob/grep), permission system, and multi-LLM support (✅ IMPLEMENTED - see [OPENCODE_COMPLETE_GUIDE.md](OPENCODE_COMPLETE_GUIDE.md))

**Model Configuration Priority:**
1. Frontend-configured models (stored in localStorage) - **HIGHEST PRIORITY**
2. Environment variables in `backend/.env` - fallback only

### Backend Architecture (FastAPI)

**Service Layer Pattern:**
- `services/llm_service.py`: Handles all LLM provider integrations, context building, and language constraints
- `services/agent_service.py`: Manages agent mode streaming, tool calling iterations, and MCP integration
- `services/code_service.py`: ✅ OpenCode-style development agent with 6 core tools (read/write/edit/bash/glob/grep), iterative tool calling (max 20 iterations), and multi-LLM support (Gemini, OpenAI, DeepSeek, Kimi, QWen, Skywork Router)
- `services/permission_service.py`: ✅ Fine-grained permission control for code operations with wildcard matching (allow/deny/ask rules)
- `services/file_service.py`: File processing with intelligent chunking (uses summarization for files >50KB)
- `services/conversation_service.py`: SQLite-based conversation persistence
- `services/mcp_client.py`: MCP protocol client for external tool servers
- `services/skill_manager.py`: Built-in skill registry (file operations, code execution, etc.)

**Important Implementation Details:**
- `LLMService.generate_response()` accepts `model_config` dict to override environment variables
- `AgentService.generate_stream()` yields SSE events: `text`, `tool_call`, `tool_result`, `thinking`, `error`, `done`
- `CodeService.generate_code_stream()` yields SSE events: `text`, `tool_call`, `tool_result`, `permission_required`, `error`, `done`, `metadata` (✅ IMPLEMENTED)
- File service automatically chunks large files and uses LLM-based summarization for context optimization
- Conversation service maintains last 10 turns by default for context window management

### Frontend Architecture (React + TypeScript)

**Component Hierarchy:**
```
App.tsx (mode selector: Chat/Agent/Code)
├── UserMenu.tsx (avatar dropdown)
│   ├── ModelSettings.tsx (modal for configuring LLM providers)
│   ├── LanguageSettings.tsx (response language constraints)
│   └── AboutDialog.tsx
├── ConversationList.tsx (sidebar with history)
├── ChatWindow.tsx (chat mode interface)
│   ├── MessageList.tsx
│   ├── MessageInput.tsx
│   └── FileUpload.tsx
├── CodeWindow.tsx ✅ (code mode interface - 270 lines)
│   ├── Welcome screen with model info and tool cards
│   ├── Real-time tool execution visualization
│   └── Anime-style UI with pink gradients
├── AgentSettings.tsx (enable/disable MCP and skills)
└── CursorEffect.tsx (UI enhancements)
```

**State Management:**
- `services/modelConfig.ts`: localStorage-based model configuration persistence
- `services/languageConfig.ts`: language preference persistence
- `services/api.ts`: API client with both REST and SSE support

**Critical Frontend Flow:**
1. User configures models via ModelSettings → saved to localStorage
2. On chat send → modelConfig passes selected model to backend via `llm_config` field
3. Backend uses `llm_config` if present, otherwise falls back to `.env`

## Development Commands

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py  # Runs on http://localhost:8000
```

**Frontend:**
```bash
cd frontend
npm install
npm start  # Runs on http://localhost:3000
```

### Docker Development

```bash
# Start services
make up

# View logs
make logs              # All logs
make logs-backend      # Backend only
make logs-frontend     # Frontend only

# Rebuild specific service
make rebuild-backend
make rebuild-frontend

# Shell access
make shell-backend
make shell-frontend

# Stop services
make down
```

### Testing

**Backend tests (>83% coverage):**
```bash
cd backend
source venv/bin/activate
pytest                                    # Run all tests
pytest tests/test_code_tools.py           # Code mode tool tests
pytest tests/test_code_api.py             # Code mode API tests
pytest --cov=. --cov-report=html         # With coverage report
./run_tests.sh all                       # Run tests + generate HTML report
```

**Frontend tests:**
```bash
cd frontend
npm test
npm run test:coverage
```

**Agent mode manual testing:**
```bash
cd backend
python test_agent.py  # Requires model configured in .env
```

## Key Implementation Patterns

### Adding a New LLM Provider

**Code Mode and Agent Mode use different service implementations:**

**For Code Mode (`services/code_service.py`):**
1. Code service routes providers as: `gemini` → `skywork_router` → OpenAI-compatible (openai/deepseek/kimi/qwen/etc.)
2. Skywork Router requires special authentication (app_key header)
3. All other providers use OpenAI-compatible API
4. Example for adding a new OpenAI-compatible provider:
```python
# No changes needed in code_service.py - it automatically supports
# any OpenAI-compatible API via base_url configuration
```

**For Chat/Agent Mode (`services/llm_service.py`):**
1. Add platform config to `PLATFORM_CONFIG` dict:
```python
"new_provider": {
    "base_url": "https://api.example.com/v1",
    "default_model": "example-model-name",
}
```

2. Update `_call_openai_compatible()` if API is OpenAI-compatible, or add new method for custom API

3. Add platform option to `frontend/src/components/ModelSettings.tsx`

4. Test with both Chat and Agent modes

### Understanding Agent Mode Tool Calling

Agent mode uses an **iterative loop** (max 10 iterations by default):

1. Send messages + available tools to LLM
2. If LLM responds with tool calls:
   - Execute tools via MCP client or skill manager
   - Append tool results to conversation
   - Go to step 1
3. If LLM responds with text (no tool calls):
   - Stream final response and exit

**Stream Event Types:**
- `thinking`: LLM reasoning about what tool to use
- `tool_call`: LLM decided to call a tool
- `tool_result`: Tool execution result
- `text`: Final text response (streamed word-by-word)
- `error`: Error occurred
- `done`: Stream complete

### File Upload Processing Logic

Files go through 3-tier processing based on size:

1. **Small files (<20KB)**: Included in full in context
2. **Medium files (20-50KB)**: Text chunked into sections
3. **Large files (>50KB)**: Sent to LLM for intelligent summarization before adding to context

This optimization prevents context window overflow while preserving important information.

### Language Constraint System

When user selects a language (e.g., "简体中文"), the system:
1. Adds a system message: "You must respond in 简体中文 regardless of input language"
2. This constraint is included in both Chat and Agent mode
3. "auto" mode means no language constraint

## Code Mode Development (✅ IMPLEMENTED)

Code Mode provides OpenCode-inspired development tools integrated into the existing Chat/Agent system. See [OPENCODE_COMPLETE_GUIDE.md](OPENCODE_COMPLETE_GUIDE.md) for comprehensive documentation.

### Core Tools (6 tools implemented)

**File Operations:**
- `read`: Read file contents with line numbers (cat -n style), supports pagination (2000 lines/page), multiple encodings
- `write`: Create or overwrite files with auto parent directory creation and overwrite warnings
- `edit`: Exact string replacement in files with uniqueness checks and diff statistics
- `glob`: File pattern matching with recursive search (`**/*.py`), sorted output, relative paths
- `grep`: Content search with regex support, case control, result limits (500 matches)

**Command Execution:**
- `bash`: Execute shell commands with timeout control (1-300 seconds), workspace isolation, dangerous command blocking

### Permission System

Default security rules in `services/permission_service.py`:
```python
{
    "read": {"*": "allow", "*.env": "ask", "*.key": "ask"},
    "write": {"*": "allow", "/etc/*": "deny"},
    "edit": {"*": "allow", "/etc/*": "deny"},
    "bash": {
        "*": "ask",           # All commands require confirmation by default
        "ls *": "allow",      # Safe commands auto-allowed
        "cat *": "allow",
        "rm *": "deny",       # Dangerous commands blocked
        "sudo *": "deny"
    }
}
```

**Permission Actions:**
- `allow`: Execute without confirmation
- `deny`: Block execution completely
- `ask`: Require user confirmation (not yet implemented in UI)

**Wildcard Patterns:**
- `*`: Matches any single path component (e.g., `*.py` matches `test.py` but not `dir/test.py`)
- `**`: Matches any path recursively (e.g., `**/*.py` matches `dir/subdir/test.py`)

### Code Service Architecture

**Multi-LLM Support:**
```python
# services/code_service.py routing logic:
if provider == "gemini":
    response = await self._call_gemini_with_tools(...)
elif provider == "skywork_router":
    response = await self._call_skywork_router_with_tools(...)
else:
    # OpenAI-compatible (openai, deepseek, kimi, qwen, etc.)
    response = await self._call_openai_with_tools(...)
```

**Supported LLM Providers:**
- Gemini (Google Generative AI)
- OpenAI (GPT-3.5, GPT-4, GPT-4o, etc.)
- DeepSeek (deepseek-chat, deepseek-coder)
- Kimi (Moonshot AI)
- QWen (Alibaba Tongyi Qianwen)
- Skywork Router (with special app_key authentication)
- Any OpenAI-compatible API providers

**Iterative Tool Calling:**
- Max 20 iterations (vs Agent mode's 10)
- Each iteration: LLM → tool calls → execute → append results → repeat
- Stops when: (1) no tool calls, (2) max iterations reached, (3) error occurs

**SSE Stream Events:**
- `text`: Assistant's text response content
- `tool_call`: LLM decided to execute a tool
- `tool_result`: Tool execution result
- `permission_required`: User confirmation needed (not yet in UI)
- `error`: Error occurred during execution
- `done`: Stream complete
- `metadata`: Conversation ID and other metadata

### Frontend Integration

**CodeWindow Component** (`frontend/src/components/CodeWindow.tsx` - 270 lines):

**Features:**
- Welcome screen with current model info, tool cards, and quick examples
- Real-time tool execution visualization
- Workspace path configuration
- SSE streaming with event handling
- Model configuration check before sending
- Anime-style UI matching existing design

**Key UI Elements:**
```typescript
// Model configuration check
const defaultModel = modelConfigService.getDefault();
if (!defaultModel) {
    // Show error message with instructions
}

// Send message with model config
const llmConfig = {
    provider: defaultModel.platform,
    api_key: defaultModel.apiKey,
    model_name: defaultModel.modelName,
    base_url: defaultModel.baseUrl || undefined,
};

await sendCodeMessage({
    message: content,
    conversation_id: conversationId,
    history: messages,
    llm_config: llmConfig,
    language: language,
    workspace_root: workspaceRoot || undefined,
    max_iterations: 20,
}, onEvent);
```

**Styling** (`frontend/src/components/CodeWindow.css` - 520+ lines):
- Pink gradient color scheme (#ff69b4, #87ceeb, #ffb6c1)
- Glassmorphism effects with backdrop-filter
- Smooth animations and transitions
- Tool call cards with hover effects
- Responsive design for mobile/desktop

### Testing Code Mode

**Unit Tests** (`backend/tests/test_code_tools.py` - 138 lines):
```bash
cd backend
pytest tests/test_code_tools.py -v
# Tests all 6 tools with various scenarios
```

**API Tests** (`backend/tests/test_code_api.py` - 150 lines):
```bash
cd backend
pytest tests/test_code_api.py -v
# Tests /api/code/chat and /api/code/tools endpoints
```

**Manual Testing:**
1. Start backend: `cd backend && python main.py`
2. Start frontend: `cd frontend && npm start`
3. Navigate to http://localhost:3000
4. Click "Code" mode button
5. Configure LLM model if not already set
6. Try example commands:
   - "List all Python files"
   - "Read the README.md file"
   - "Find all TODO comments"
   - "Show git status"

### Adding New Code Tools

To add a new tool (e.g., `format`):

1. Define tool schema in `services/code_service.py`:
```python
def _tool_format(self) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "format",
            "description": "Format code using a formatter",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "formatter": {"type": "string", "enum": ["black", "prettier"]}
                },
                "required": ["file_path", "formatter"]
            }
        }
    }
```

2. Implement execution method:
```python
async def execute_format(self, file_path: str, formatter: str):
    # Check permission
    perm = self.permission_service.check("format", file_path)
    if perm == "deny":
        return {"error": "Permission denied"}
    if perm == "ask":
        yield {"type": "permission_required", "action": "format", "target": file_path}
        # Wait for user confirmation (future implementation)

    # Execute formatter
    full_path = os.path.join(self.workspace_root, file_path)
    # ... formatting logic
```

3. Add to `_get_code_tools()` list:
```python
def _get_code_tools(self) -> List[dict]:
    return [
        self._tool_read(),
        self._tool_write(),
        # ... existing tools
        self._tool_format(),  # Add new tool
    ]
```

4. Add permission rules to `services/permission_service.py`:
```python
"format": {
    "*": "allow",
    "*.lock": "deny",  # Don't format lock files
}
```

5. Write tests in `tests/test_code_tools.py`

### Common Code Mode Issues

**Error: "Model configuration is missing"**
- Cause: No model configured in frontend
- Solution: Click user menu → Model Settings → Add a model

**Error: "Workspace not found"**
- Cause: Invalid workspace_root path
- Solution: Enter a valid absolute path or leave empty for current directory

**Tool execution hangs:**
- Cause: Command timeout (default 30s for bash)
- Solution: Increase timeout or optimize command

**Permission denied errors:**
- Check `permission_service.py` default rules
- Modify rules or implement "ask" confirmation UI

### Why Code Mode is Separate

Code Mode is intentionally separate from Chat/Agent modes because:

1. **Different use case**: Development tasks vs conversational AI vs task automation
2. **Different tool set**: File operations + bash vs general tools vs MCP + skills
3. **Different iteration limit**: 20 (code) vs 10 (agent) vs 1 (chat)
4. **Different permission model**: Fine-grained file/command control vs open tool calling
5. **Different UX**: Tool visualization vs chat flow vs agent thinking

All three modes share:
- Same model configuration system (localStorage)
- Same conversation persistence (SQLite)
- Same LLM service layer (multi-provider support)
- Same UI design language (anime-style)

## Common Development Scenarios

### Debugging Backend Issues

1. Check backend logs: `make logs-backend` or `docker-compose logs -f backend`
2. Access API docs: http://localhost:8000/docs (Swagger UI)
3. Test endpoints manually via `/docs` interactive interface
4. Check SQLite database: `backend/data/conversations.db`

### Adding a New Agent Skill

1. Add skill class to `services/skill_manager.py`:
```python
class NewSkill(BaseSkill):
    def get_tool_definition(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "new_skill_name",
                "description": "What this skill does",
                "parameters": { ... }
            }
        }

    async def execute(self, **kwargs) -> str:
        # Implement skill logic
        return result
```

2. Register in `SkillManager.__init__()`:
```python
self.skills["new_skill_name"] = NewSkill()
```

3. Test via agent mode

### Using Code Mode for Development Tasks

Code Mode is ideal for:
- Reading and analyzing existing code
- Making precise edits to files
- Searching for patterns across the codebase
- Executing development commands (git, npm, pytest, etc.)
- Exploring project structure

**Best Practices:**
1. Always set a workspace_root to limit file access
2. Review permission rules before sensitive operations
3. Use `read` before `edit` to verify content
4. Prefer `edit` over `write` for existing files (safer)
5. Set appropriate bash timeouts for long-running commands

**Example workflows:**
```
"Read package.json and show all dependencies"
"Find all TODO comments in Python files"
"Run pytest and show the results"
"Edit main.py to add error handling to the send_message function"
"Search for all imports of llm_service"
```

### Modifying Context Window Size

Edit `services/conversation_service.py`:
```python
def get_conversation_messages(self, conversation_id: str, limit: int = 10):
```
Change `limit` parameter to adjust how many turns are included in context.

**Note**: Code Mode uses a different context strategy - it includes the full conversation history without a turn limit, relying on the 20-iteration cap to prevent runaway loops.

### Adding Code Mode Tools (Future)

When implementing Code Mode tools in `services/code_service.py`:

1. Define tool using OpenAI function calling format:
```python
def _tool_read(self) -> dict:
    return {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read file contents with pagination",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "offset": {"type": "integer"},
                    "limit": {"type": "integer"}
                },
                "required": ["file_path"]
            }
        }
    }
```

2. Implement execution method:
```python
async def execute_read(self, file_path: str, offset: int = 0, limit: int = 2000):
    # Check permission
    perm = self.permission_service.check("read", file_path)
    if perm == "deny":
        return {"error": "Permission denied"}
    if perm == "ask":
        yield {"type": "permission_required", "action": "read", "target": file_path}
        # Future: wait for user confirmation

    # Execute operation
    full_path = os.path.join(self.workspace_root, file_path)
    # ... read file logic with line numbers (cat -n style)
```

3. Register tool in `_get_code_tools()` method

4. Test with various permission configurations

**See "Code Mode Development" section above for the complete implementation guide of the 6 existing tools.**

## Testing Strategy

The test suite covers:
- **API endpoints**: Request/response handling, validation, error cases
- **LLM service**: Multiple providers, dynamic config, context building
- **File service**: All formats, size limits, chunking, summarization
- **Conversation service**: CRUD operations, message threading
- **Agent service**: Tool calling flow, streaming (mocked)
- **Code tools**: All 6 tools (read/write/edit/bash/glob/grep) with various scenarios (✅ 17/17 tests passing)
- **Code API**: SSE streaming, model config, tool execution (✅ integrated tests)

Run full test suite before submitting PRs:
```bash
cd backend && ./run_tests.sh all
cd ../frontend && npm test
```

**Test file organization:**
- `backend/tests/test_api.py` - Main API endpoints
- `backend/tests/test_llm_service.py` - LLM provider tests
- `backend/tests/test_file_service.py` - File processing tests
- `backend/tests/test_conversation_service.py` - Conversation DB tests
- `backend/tests/test_agent.py` - Agent mode tests
- `backend/tests/test_code_tools.py` - Code mode tool tests (138 lines)
- `backend/tests/test_code_api.py` - Code mode API tests (150 lines)

## Deployment

**Production deployment uses Docker Compose** with separate containers:
- Backend: FastAPI + Uvicorn (port 8000)
- Frontend: React static build served by Nginx (port 3000)
- Shared network: `chatbot-network` (bridge)

**Data persistence:**
- Database: `./backend/data/` mounted as volume
- Environment: `./backend/.env` mounted read-only

**Health checks:**
- Backend: HTTP GET to `/health` endpoint
- Frontend: HTTP GET to `/health` (nginx serves static fallback)

## Important Notes

- Python 3.8-3.13 supported (NOT 3.14 yet)
- Frontend model config takes priority over backend `.env`
- Agent mode requires streaming-compatible LLM (tool calling support)
- Code mode requires function calling support (all tested LLMs support this)
- SQLite database is created automatically on first run
- CORS is wide open (`allow_origins=["*"]`) - restrict in production
- API keys in localStorage are NOT encrypted - consider security implications for production
- Code mode workspace isolation protects against accidental file operations outside the workspace
- Permission system defaults to "ask" for bash commands for security (not yet in UI)

## Roadmap & Future Development

### Code Mode Enhancements (Future)

**Current Status:** ✅ Code Mode fully implemented with 6 core tools, permission system, multi-LLM support, and anime-style UI

**Potential Future Enhancements:**
- **Permission confirmation UI**: Implement "ask" permission dialog in frontend
- **File tree browser**: Visual workspace file explorer
- **Code syntax highlighting**: Enhanced result display with language-specific highlighting
- **Conversation persistence**: Save Code Mode conversations to database (currently in-memory only)
- **LSP integration**: Optional language server protocol for code intelligence (autocomplete, go-to-definition)
- **More tools**: Consider adding `find_replace_all`, `run_tests`, `git_diff`, `create_file_from_template`

See [OPENCODE_COMPLETE_GUIDE.md](OPENCODE_COMPLETE_GUIDE.md) for detailed implementation history and architecture decisions.
