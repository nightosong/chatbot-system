# Agent Service 上下文功能修复

## 问题描述

在测试 agent_service 时发现没有上下文功能，即多轮对话中模型无法记住之前的工具调用和对话历史。

## 根本原因

1. **数据库层面**：`conversation_service` 只保存了简单的 user 和 assistant 消息（role + content），没有保存工具调用的详细信息（tool_calls、tool_call_id 等）
2. **消息构建层面**：`_build_messages` 方法在处理历史消息时，没有正确处理工具调用相关的字段
3. **消息保存层面**：每次对话结束后只保存了最终的文本回复，丢失了中间的工具调用上下文

## 修复方案

### 1. 扩展数据库结构

在 `messages` 表中添加 `metadata` 字段来存储工具调用信息：

```python
# conversation_service.py
# 添加 metadata 列
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TEXT,
    file_context TEXT,
    metadata TEXT,  -- 新增：存储 tool_calls 等信息
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
)
```

### 2. 新增 save_messages 方法

添加新方法来保存完整的消息历史（包括工具调用）：

```python
def save_messages(
    self,
    messages: List[dict],
    conversation_id: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """保存完整的消息历史，包括工具调用信息"""
    # 实现详见 conversation_service.py
```

### 3. 更新 get_conversation_messages 方法

从数据库读取消息时，解析 metadata 并还原完整的消息结构：

```python
def get_conversation_messages(self, conversation_id: str) -> List[dict]:
    """获取完整的消息历史，包括工具调用信息"""
    # 从 metadata 中还原 tool_calls 和 tool_call_id
```

### 4. 修复 _build_messages 方法

在构建消息时，正确处理历史消息中的工具调用：

```python
# agent_service.py
# 现在会包含 tool_calls 和 tool_call_id
for msg in conversation_history[-20:]:
    role = msg.get("role", "user")
    history_msg = {"role": role, "content": content}

    # 包含工具调用信息
    if role == "assistant" and "tool_calls" in msg:
        history_msg["tool_calls"] = msg["tool_calls"]

    if role == "tool" and "tool_call_id" in msg:
        history_msg["tool_call_id"] = msg["tool_call_id"]
```

### 5. 更新流式生成方法

各个 provider 的流式生成方法在完成后返回完整的消息历史：

```python
# 在迭代结束后返回完整消息
conversation_messages = [msg for msg in current_messages if msg.get("role") != "system"]
yield {"type": "done", "messages": conversation_messages}
```

### 6. 更新 main.py 保存逻辑

使用新的 `save_messages` 方法保存完整的对话历史：

```python
# main.py
if final_messages:
    conversation_id = conversation_service.save_messages(
        messages=final_messages,
        conversation_id=request.conversation_id,
    )
```

## 数据库迁移

如果已有数据库，需要运行迁移脚本：

```bash
cd chatbot-system/backend
python scripts/migrate_db.py
```

## 测试方法

### 1. 基础上下文测试

```bash
# 第一轮：让 AI 计算一个值
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请帮我计算 123 * 456",
    "llm_config": {
      "provider": "openai",
      "api_key": "YOUR_API_KEY",
      "model_name": "gpt-4"
    },
    "agent_config": {
      "enable_mcp": true,
      "enable_skills": true
    }
  }'

# 保存返回的 conversation_id

# 第二轮：引用第一轮的结果
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "刚才的结果是多少？请再乘以2",
    "conversation_id": "CONVERSATION_ID_FROM_FIRST_ROUND",
    "llm_config": {
      "provider": "openai",
      "api_key": "YOUR_API_KEY",
      "model_name": "gpt-4"
    },
    "agent_config": {
      "enable_mcp": true,
      "enable_skills": true
    }
  }'
```

### 2. 工具调用上下文测试

```bash
# 第一轮：使用工具获取信息
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请帮我分析这组数据：[10, 20, 30, 40, 50]，计算平均值和标准差",
    "llm_config": {...},
    "agent_config": {...}
  }'

# 第二轮：引用第一轮的分析结果
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "根据刚才的分析结果，如果我再添加一个60，平均值会变成多少？",
    "conversation_id": "CONVERSATION_ID",
    "llm_config": {...},
    "agent_config": {...}
  }'
```

### 3. 验证数据库

```python
import sqlite3

conn = sqlite3.connect("data/conversations.db")
cursor = conn.cursor()

# 检查消息是否包含 metadata
cursor.execute("SELECT role, content, metadata FROM messages WHERE conversation_id = ?",
               (conversation_id,))

for row in cursor.fetchall():
    print(f"Role: {row[0]}")
    print(f"Content: {row[1]}")
    print(f"Metadata: {row[2]}")
    print("-" * 60)

conn.close()
```

## 预期效果

修复后，agent_service 应该能够：

1. ✅ 记住多轮对话的历史
2. ✅ 记住之前的工具调用和结果
3. ✅ 在新的对话中引用之前的信息
4. ✅ 保持完整的对话上下文（包括 user、assistant、tool 消息）

## 文件修改清单

- ✅ `services/conversation_service.py` - 添加 metadata 支持
- ✅ `services/agent_service.py` - 修复消息构建和流式生成
- ✅ `main.py` - 更新消息保存逻辑
- ✅ `scripts/migrate_db.py` - 数据库迁移脚本

## 注意事项

1. 现有的旧数据库需要运行迁移脚本
2. 保留了旧的 `save_message` 方法以保持向后兼容
3. 系统消息不会被保存到对话历史中
4. 默认保留最近20条历史消息（可调整）
