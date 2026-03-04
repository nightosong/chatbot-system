import React, { useState, useEffect, useRef } from 'react';
import './ChatWindow.css';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import FileUpload from './FileUpload';
import { Message, ChatMode, ToolCall } from '../types';
import { sendMessage, sendAgentMessage, getConversation } from '../services/api';
import { modelConfigService } from '../services/modelConfig';
import { languageConfigService } from '../services/languageConfig';
import { agentConfigService } from '../services/agentConfig';

interface ChatWindowProps {
  conversationId: string | null;
  onConversationUpdate: () => void;
  onConversationIdChange?: (id: string) => void;
  chatMode: ChatMode;
}

const ChatWindow: React.FC<ChatWindowProps> = ({ 
  conversationId, 
  onConversationUpdate,
  onConversationIdChange,
  chatMode,
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [fileContext, setFileContext] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [streamingContent, setStreamingContent] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversation when conversationId changes
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      setMessages([]);
      setFileContext(null);
      setFileName(null);
    }
  }, [conversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversation = async (id: string) => {
    try {
      setIsLoading(true);
      const data = await getConversation(id);
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() && !fileContext) return;

    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // 获取默认模型配置
    const defaultModel = modelConfigService.getDefault();
    const llmConfig = defaultModel ? {
      provider: defaultModel.platform,
      api_key: defaultModel.apiKey,
      model_name: defaultModel.modelName,
      base_url: defaultModel.baseUrl || undefined,
    } : null;

    // 获取语言设置
    const language = languageConfigService.getLanguage();

    try {
      setIsLoading(true);

      if (chatMode === 'agent') {
        // Agent mode with streaming
        await handleAgentMessage(content, llmConfig, language);
      } else {
        // Regular chat mode
        await handleChatMessage(content, llmConfig, language);
      }

      // Clear file context after sending
      setFileContext(null);
      setFileName(null);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: Message = {
        role: 'assistant',
        content: '❌ Sorry, there was an error processing your message. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChatMessage = async (
    content: string,
    llmConfig: any,
    language: string | null
  ) => {
    const response = await sendMessage({
      message: content,
      conversation_id: conversationId,
      file_context: fileContext,
      llm_config: llmConfig,
      language: language,
    });

    // Add assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: response.message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Update conversation ID if this is a new conversation
    if (!conversationId && response.conversation_id && onConversationIdChange) {
      onConversationIdChange(response.conversation_id);
    }

    // Update conversation list
    onConversationUpdate();
  };

  const handleAgentMessage = async (
    content: string,
    llmConfig: any,
    language: string | null
  ) => {
    // Reset streaming state
    setStreamingContent('');
    setToolCalls([]);

    // Get agent config
    const agentConfig = agentConfigService.getAgentConfig();

    let fullContent = '';
    const currentToolCalls: ToolCall[] = [];

    await sendAgentMessage(
      {
        message: content,
        conversation_id: conversationId,
        file_context: fileContext,
        llm_config: llmConfig,
        language: language,
        agent_config: agentConfig,
      },
      (event) => {
        if (event.type === 'text') {
          fullContent += event.content || '';
          setStreamingContent(fullContent);
        } else if (event.type === 'tool_call') {
          const toolCall: ToolCall = {
            tool: event.tool || '',
            args: event.args || {},
          };
          currentToolCalls.push(toolCall);
          setToolCalls([...currentToolCalls]);
        } else if (event.type === 'tool_result') {
          // Update the last tool call with result
          if (currentToolCalls.length > 0) {
            const lastTool = currentToolCalls[currentToolCalls.length - 1];
            lastTool.result = event.result;
            setToolCalls([...currentToolCalls]);
          }
        } else if (event.type === 'metadata') {
          // Update conversation ID if this is a new conversation
          if (!conversationId && event.conversation_id && onConversationIdChange) {
            onConversationIdChange(event.conversation_id);
          }
          // Update conversation list
          onConversationUpdate();
        } else if (event.type === 'error') {
          fullContent += `\n\n❌ Error: ${event.content}`;
          setStreamingContent(fullContent);
        }
      }
    );

    // Add final assistant message
    const assistantMessage: Message = {
      role: 'assistant',
      content: fullContent,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMessage]);

    // Clear streaming state
    setStreamingContent('');
    setToolCalls([]);
  };

  const handleFileUpload = (content: string, filename: string) => {
    setFileContext(content);
    setFileName(filename);
  };

  const handleRemoveFile = () => {
    setFileContext(null);
    setFileName(null);
  };

  return (
    <div className="chat-window">
      <div className="chat-content">
        {messages.length === 0 && !isLoading ? (
          <div className="welcome-message">
            <h2>🌟 欢迎来到 AI Chat System 💫</h2>
            <p>开始对话或上传文件吧~ ✨</p>
            <div className="features">
              <div className="feature feature-chat">
                <div className="feature-icon-wrapper">
                  <div className="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="url(#gradient1)"/>
                      <circle cx="8" cy="9" r="1.5" fill="white"/>
                      <circle cx="12" cy="9" r="1.5" fill="white"/>
                      <circle cx="16" cy="9" r="1.5" fill="white"/>
                      <path d="M7 13C7 13 8.5 15 12 15C15.5 15 17 13 17 13" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                      <defs>
                        <linearGradient id="gradient1" x1="2" y1="2" x2="22" y2="22">
                          <stop offset="0%" stopColor="#ff9a9e"/>
                          <stop offset="100%" stopColor="#fecfef"/>
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                </div>
                <span className="feature-title">多轮对话</span>
                <span className="feature-desc">智能上下文理解</span>
              </div>
              <div className="feature feature-file">
                <div className="feature-icon-wrapper">
                  <div className="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="url(#gradient2)"/>
                      <path d="M14 2V8H20" fill="url(#gradient2)" opacity="0.7"/>
                      <path d="M8 12H16M8 16H13" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
                      <defs>
                        <linearGradient id="gradient2" x1="4" y1="2" x2="20" y2="22">
                          <stop offset="0%" stopColor="#a8edea"/>
                          <stop offset="100%" stopColor="#fed6e3"/>
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                </div>
                <span className="feature-title">文件上传</span>
                <span className="feature-desc">支持文档/图片/视频/音频</span>
              </div>
              <div className="feature feature-history">
                <div className="feature-icon-wrapper">
                  <div className="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2Z" fill="url(#gradient3)"/>
                      <path d="M12 6V12L16 14" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <defs>
                        <linearGradient id="gradient3" x1="2" y1="2" x2="22" y2="22">
                          <stop offset="0%" stopColor="#ffecd2"/>
                          <stop offset="100%" stopColor="#fcb69f"/>
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>
                </div>
                <span className="feature-title">对话历史</span>
                <span className="feature-desc">随时回顾聊天</span>
              </div>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} isLoading={isLoading} />
            {streamingContent && (
              <div className="streaming-message">
                <div className="message assistant">
                  <div className="message-content">{streamingContent}</div>
                  <div className="streaming-indicator">
                    <span className="dot"></span>
                    <span className="dot"></span>
                    <span className="dot"></span>
                  </div>
                </div>
              </div>
            )}
            {toolCalls.length > 0 && (
              <div className="tool-calls-container">
                {toolCalls.map((toolCall, index) => (
                  <div key={index} className="tool-call">
                    <div className="tool-call-header">
                      <span className="tool-icon">🔧</span>
                      <span className="tool-name">{toolCall.tool}</span>
                    </div>
                    <div className="tool-call-args">
                      {JSON.stringify(toolCall.args, null, 2)}
                    </div>
                    {toolCall.result && (
                      <div className="tool-call-result">
                        <span className="result-label">Result:</span>
                        <pre>{toolCall.result}</pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <FileUpload onFileUpload={handleFileUpload} />
        {fileName && (
          <div className="file-indicator">
            <span>📎 {fileName}</span>
            <button onClick={handleRemoveFile} className="remove-file-btn">✕</button>
          </div>
        )}
        <MessageInput onSendMessage={handleSendMessage} disabled={isLoading} />
      </div>
    </div>
  );
};

export default ChatWindow;
