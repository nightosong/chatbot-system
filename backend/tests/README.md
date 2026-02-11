# 测试套件说明

本目录包含 AI Chat System 后端的完整测试套件。

## 📁 测试文件结构

```
tests/
├── conftest.py                    # Pytest 配置和共享 fixtures
├── test_api.py                    # API 端点测试
├── test_llm_service.py            # LLM 服务测试
├── test_conversation_service.py   # 对话服务测试
├── test_file_service.py           # 文件服务测试
├── test_context.py                # 上下文记忆集成测试（可执行脚本）
└── test-data/                     # 测试数据文件
    ├── sample.txt
    └── sample.md
```

## 🧪 测试类型

### 单元测试 (Unit Tests)
使用 pytest 框架，测试各个组件的独立功能：

- **test_api.py**: 测试所有 FastAPI 端点
  - 健康检查
  - 聊天功能（新对话、现有对话、文件上下文、模型配置）
  - 对话管理（获取、删除）
  - 文件上传

- **test_llm_service.py**: 测试 LLM 服务
  - 服务初始化（环境变量/用户配置）
  - 平台配置管理
  - 上下文构建（Gemini/OpenAI）
  - 响应生成
  - 错误处理

- **test_conversation_service.py**: 测试对话服务
  - 数据库初始化
  - 消息保存和检索
  - 对话历史管理
  - 对话删除

- **test_file_service.py**: 测试文件服务
  - 文件上传和处理
  - 格式支持（txt, md, pdf）
  - 文件大小限制
  - 智能摘要策略

### 集成测试 (Integration Tests)
- **test_context.py**: 可执行脚本，测试多轮对话的上下文记忆功能

## 🚀 运行测试

### 运行所有测试
```bash
cd backend
pytest tests/ -v
```

### 运行特定测试文件
```bash
pytest tests/test_api.py -v
pytest tests/test_llm_service.py -v
```

### 运行特定测试类或函数
```bash
# 运行特定测试类
pytest tests/test_llm_service.py::TestLLMServiceInitialization -v

# 运行特定测试函数
pytest tests/test_api.py::test_root_endpoint -v
```

### 查看测试覆盖率
```bash
pytest tests/ --cov=services --cov=main --cov-report=html
```

### 运行集成测试脚本
```bash
# 需要配置真实的 API Key
python tests/test_context.py
```

## 📊 测试覆盖范围

### API 端点 (test_api.py)
- ✅ GET `/` - 健康检查
- ✅ POST `/api/chat` - 聊天（新对话、现有对话、文件上下文、模型配置）
- ✅ GET `/api/conversations` - 获取所有对话
- ✅ GET `/api/conversations/{id}` - 获取特定对话
- ✅ DELETE `/api/conversations/{id}` - 删除对话
- ✅ POST `/api/upload` - 文件上传

### LLM 服务 (test_llm_service.py)
- ✅ 服务初始化（有/无环境变量）
- ✅ 平台配置（DeepSeek, Kimi, QWen, OpenAI, Gemini）
- ✅ 上下文构建（Gemini 字符串格式）
- ✅ 消息构建（OpenAI 数组格式）
- ✅ 历史记录截断（最多20条）
- ✅ 用户配置优先级
- ✅ 环境变量回退
- ✅ 错误处理（缺少 API key、模型名称）

### 对话服务 (test_conversation_service.py)
- ✅ 数据库初始化
- ✅ 新对话创建
- ✅ 现有对话追加
- ✅ 消息检索
- ✅ 对话列表
- ✅ 对话删除
- ✅ 文件上下文保存
- ✅ 标题生成
- ✅ 对话排序

### 文件服务 (test_file_service.py)
- ✅ 文本文件处理
- ✅ Markdown 文件处理
- ✅ 不支持格式错误处理
- ✅ 文件大小限制
- ✅ 文件扩展名提取
- ✅ 文本分块
- ✅ 中等文件摘要
- ✅ 大文件激进摘要
- ✅ 智能摘要生成

## 🔧 Fixtures 说明

### conftest.py 提供的共享 fixtures:

- `setup_test_environment`: 设置测试环境变量
- `test_client`: FastAPI 测试客户端
- `temp_db`: 临时数据库（自动清理）
- `mock_llm_service`: 模拟 LLM 服务
- `mock_conversation_service`: 模拟对话服务
- `sample_conversation_history`: 示例对话历史
- `sample_model_config`: 示例模型配置

## 📝 编写新测试

### 示例：添加新的 API 测试

```python
def test_new_endpoint(test_client, mock_llm_service):
    """Test description"""
    response = test_client.get("/api/new-endpoint")
    
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### 示例：添加异步测试

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await some_async_function()
    assert result == expected_value
```

## 🐛 调试测试

### 显示打印输出
```bash
pytest tests/ -v -s
```

### 只运行失败的测试
```bash
pytest tests/ --lf
```

### 进入调试器
```bash
pytest tests/ --pdb
```

## ✅ 最佳实践

1. **测试隔离**: 每个测试应该独立运行，不依赖其他测试
2. **使用 Fixtures**: 重用测试数据和设置
3. **清晰命名**: 测试函数名应该描述测试内容
4. **断言具体**: 使用具体的断言而不是模糊的检查
5. **Mock 外部依赖**: 使用 mock 避免实际 API 调用
6. **测试边界情况**: 包括正常情况和错误情况

## 📚 参考资料

- [Pytest 文档](https://docs.pytest.org/)
- [FastAPI 测试](https://fastapi.tiangolo.com/tutorial/testing/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
