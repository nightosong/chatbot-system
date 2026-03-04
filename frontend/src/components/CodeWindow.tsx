import React, { useState, useEffect, useRef } from 'react';
import './CodeWindow.css';
import { Message, CodeToolCall } from '../types';
import { sendCodeMessage } from '../services/api';
import { modelConfigService } from '../services/modelConfig';
import { languageConfigService } from '../services/languageConfig';

interface CodeWindowProps {
  conversationId: string | null;
  onConversationUpdate: () => void;
  onConversationIdChange?: (id: string) => void;
}

const CodeWindow: React.FC<CodeWindowProps> = ({
  conversationId,
  onConversationUpdate,
  onConversationIdChange,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [workspaceRoot, setWorkspaceRoot] = useState<string>('');
  const [toolCalls, setToolCalls] = useState<CodeToolCall[]>([]);
  const [streamingContent, setStreamingContent] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, toolCalls]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [inputValue]);

  const handleSendMessage = async () => {
    const content = inputValue.trim();
    if (!content) return;

    // Check if model is configured
    const defaultModel = modelConfigService.getDefault();
    if (!defaultModel) {
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ 请先配置 LLM 模型！\n\n请点击右上角用户菜单 → 模型设置，添加并启用一个 LLM 模型（如 OpenAI、Gemini、DeepSeek 等）。',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setToolCalls([]);
    setStreamingContent('');

    // Get model configuration
    const llmConfig = {
      provider: defaultModel.platform,
      api_key: defaultModel.apiKey,
      model_name: defaultModel.modelName,
      base_url: defaultModel.baseUrl || undefined,
    };

    // Get language setting
    const language = languageConfigService.getLanguage();

    try {
      setIsLoading(true);

      let assistantContent = '';
      const currentToolCalls: CodeToolCall[] = [];

      await sendCodeMessage(
        {
          message: content,
          conversation_id: conversationId,
          history: messages,
          llm_config: llmConfig,
          language: language,
          workspace_root: workspaceRoot || undefined,
          max_iterations: 20,
        },
        (event) => {
          console.log('Code event:', event);

          if (event.type === 'text') {
            assistantContent += event.content || '';
            setStreamingContent(assistantContent);
          } else if (event.type === 'tool_call') {
            const toolCall: CodeToolCall = {
              tool: event.tool || '',
              args: event.args || {},
              progress: [],  // Initialize progress list
            };
            currentToolCalls.push(toolCall);
            setToolCalls([...currentToolCalls]);
          } else if (event.type === 'tool_progress') {
            // Handle tool progress events
            if (currentToolCalls.length > 0) {
              const lastCall = currentToolCalls[currentToolCalls.length - 1];
              if (!lastCall.progress) {
                lastCall.progress = [];
              }
              lastCall.progress.push(event.message || '');
              setToolCalls([...currentToolCalls]);
            }
          } else if (event.type === 'tool_result') {
            // Update the last tool call with result
            if (currentToolCalls.length > 0) {
              const lastCall = currentToolCalls[currentToolCalls.length - 1];
              lastCall.result = event.result;
              setToolCalls([...currentToolCalls]);
            }
          } else if (event.type === 'permission_required') {
            // TODO: Show permission dialog
            console.warn('Permission required:', event);
            assistantContent += `\n\n⚠️ Permission required: ${event.action} on ${event.target}`;
            setStreamingContent(assistantContent);
          } else if (event.type === 'error') {
            assistantContent += `\n\n❌ Error: ${event.content}`;
            setStreamingContent(assistantContent);
          } else if (event.type === 'metadata' && event.conversation_id) {
            // Update conversation ID if this is a new conversation
            if (!conversationId && onConversationIdChange) {
              onConversationIdChange(event.conversation_id);
            }
          }
        }
      );

      // Add assistant message with final content
      if (assistantContent || currentToolCalls.length > 0) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: assistantContent || '✓ Tool execution completed',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }

      setStreamingContent('');

      // Update conversation list
      onConversationUpdate();
    } catch (error) {
      console.error('Failed to send code message:', error);
      // Add error message
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ 发送消息失败，请检查：\n\n1. 是否已配置 LLM 模型\n2. API Key 是否正确\n3. 网络连接是否正常\n\n详细错误：' + (error instanceof Error ? error.message : String(error)),
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatToolResult = (result: any): string => {
    if (typeof result === 'string') {
      return result;
    }
    return JSON.stringify(result, null, 2);
  };

  // Get current model info
  const currentModel = modelConfigService.getDefault();
  const enabledModels = modelConfigService.getEnabled();

  return (
    <div className="code-window">
      <div className="code-header">
        <div className="workspace-selector">
          <label>📁 Workspace:</label>
          <input
            type="text"
            value={workspaceRoot}
            onChange={(e) => setWorkspaceRoot(e.target.value)}
            placeholder="Enter workspace path (e.g., /path/to/project)"
            className="workspace-input"
          />
        </div>
        <div className="code-info">
          <span>Code Mode</span>
          {currentModel && (
            <span className="model-badge" title={`Provider: ${currentModel.platform}\nModel: ${currentModel.modelName}`}>
              {currentModel.platform}
            </span>
          )}
        </div>
      </div>

      <div className="code-messages">
        {/* Welcome message when no messages */}
        {messages.length === 0 && (
          <div className="code-welcome">
            <h2>✨ 欢迎使用 Code Mode ✨</h2>
            <p>AI 驱动的代码开发助手，支持文件读写、命令执行、代码搜索等功能</p>

            {currentModel ? (
              <div className="model-info">
                <div className="info-item">
                  <span className="info-label">🤖 当前模型:</span>
                  <span className="info-value">{currentModel.platform} - {currentModel.modelName}</span>
                </div>
                {enabledModels.length > 1 && (
                  <div className="info-item">
                    <span className="info-label">📋 可用模型:</span>
                    <span className="info-value">{enabledModels.length} 个</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="model-warning">
                <div className="warning-icon">⚠️</div>
                <div className="warning-text">
                  <strong>未配置 LLM 模型</strong>
                  <p>请点击右上角用户菜单 → 模型设置，添加并启用一个 LLM 模型</p>
                </div>
              </div>
            )}

            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">📖</div>
                <div className="feature-name">read</div>
                <div className="feature-desc">读取文件内容</div>
              </div>
              <div className="feature-card">
                <div className="feature-icon">✏️</div>
                <div className="feature-name">write</div>
                <div className="feature-desc">创建/写入文件</div>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔧</div>
                <div className="feature-name">edit</div>
                <div className="feature-desc">精确编辑文件</div>
              </div>
              <div className="feature-card">
                <div className="feature-icon">⚡</div>
                <div className="feature-name">bash</div>
                <div className="feature-desc">执行命令</div>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔍</div>
                <div className="feature-name">glob</div>
                <div className="feature-desc">查找文件</div>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔎</div>
                <div className="feature-name">grep</div>
                <div className="feature-desc">搜索内容</div>
              </div>
            </div>

            <div className="quick-examples">
              <div className="examples-title">💡 快速开始示例：</div>
              <div className="example-item">"List all Python files in the project"</div>
              <div className="example-item">"Read the README.md file"</div>
              <div className="example-item">"Find all TODO comments"</div>
              <div className="example-item">"Show the git status"</div>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`code-message ${message.role}`}>
            <div className="message-role">
              {message.role === 'user' ? '👤 You' : '🤖 Assistant'}
            </div>
            <div className="message-content">
              <pre>{message.content}</pre>
            </div>
            <div className="message-timestamp">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}

        {/* Show streaming content */}
        {streamingContent && (
          <div className="code-message assistant streaming">
            <div className="message-role">🤖 Assistant</div>
            <div className="message-content">
              <pre>{streamingContent}</pre>
            </div>
          </div>
        )}

        {/* Show tool calls */}
        {toolCalls.length > 0 && (
          <div className="tool-calls-container">
            <div className="tool-calls-header">🔧 Tool Executions</div>
            {toolCalls.map((call, index) => (
              <div key={index} className={`tool-call ${!call.result ? 'executing' : ''}`}>
                <div className="tool-call-header">
                  <span className="tool-name">{call.tool}</span>
                  <span className="tool-status">
                    {call.result !== undefined ? '✓' : '⏳'}
                  </span>
                </div>
                <div className="tool-call-args">
                  <strong>Arguments:</strong>
                  <pre>{JSON.stringify(call.args, null, 2)}</pre>
                </div>

                {/* Show progress messages */}
                {call.progress && call.progress.length > 0 && (
                  <div className="tool-call-progress">
                    <strong>Progress:</strong>
                    {call.progress.map((msg, i) => (
                      <div key={i} className="progress-item">
                        {msg}
                      </div>
                    ))}
                  </div>
                )}

                {call.result !== undefined && (
                  <div className="tool-call-result">
                    <strong>Result:</strong>
                    <pre>{formatToolResult(call.result)}</pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="code-input-container">
        <textarea
          ref={textareaRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Describe what you want to do with the code (e.g., 'Read the README.md file', 'List all Python files')..."
          className="code-input"
          disabled={isLoading}
          rows={1}
        />
        <button
          onClick={handleSendMessage}
          disabled={isLoading || !inputValue.trim()}
          className="code-send-button"
        >
          {isLoading ? 'Running...' : 'Send'}
        </button>
      </div>

      {isLoading && (
        <div className="code-loading-indicator">
          <div className="loading-spinner"></div>
          <span>Executing code operations...</span>
        </div>
      )}
    </div>
  );
};

export default CodeWindow;
