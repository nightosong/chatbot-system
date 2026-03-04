import React, { useState, useEffect, useRef } from 'react';
import './ChatWindow.css';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import FileUpload from './FileUpload';
import { Message, ChatMode, AgentStreamEvent } from '../types';
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

interface AgentStep {
  id: number;
  type: 'status' | 'thinking' | 'tool_call' | 'tool_result' | 'error';
  title: string;
  detail?: string;
  timestamp: string;
}

interface AgentRun {
  id: number;
  status: 'running' | 'completed' | 'error';
  steps: AgentStep[];
  startedAt: string;
  finishedAt?: string;
}

interface MediaPreviewItem {
  url: string;
  type: 'image' | 'video';
  coverUrl?: string;
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
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [collapsedRuns, setCollapsedRuns] = useState<Record<number, boolean>>({});
  const [streamingContent, setStreamingContent] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stepIdRef = useRef<number>(0);
  const runIdRef = useRef<number>(0);

  // Load conversation when conversationId changes
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      setMessages([]);
      setFileContext(null);
      setFileName(null);
      setAgentRuns([]);
      setActiveRunId(null);
      setCollapsedRuns({});
    }
  }, [conversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, agentRuns]);

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

    // Get agent config
    const agentConfig = agentConfigService.getAgentConfig();

    let fullContent = '';
    const runId = ++runIdRef.current;
    setActiveRunId(runId);
    setCollapsedRuns((prev) => ({ ...prev, [runId]: false }));
    setAgentRuns((prev) => [
      ...prev,
      {
        id: runId,
        status: 'running',
        steps: [],
        startedAt: new Date().toISOString(),
      },
    ]);

    const appendStep = (targetRunId: number, step: Omit<AgentStep, 'id' | 'timestamp'>) => {
      const nextStep: AgentStep = {
        ...step,
        id: ++stepIdRef.current,
        timestamp: new Date().toISOString(),
      };
      setAgentRuns((prev) =>
        prev.map((run) =>
          run.id === targetRunId ? { ...run, steps: [...run.steps, nextStep] } : run
        )
      );
    };

    const updateRunStatus = (targetRunId: number, status: AgentRun['status']) => {
      setAgentRuns((prev) =>
        prev.map((run) =>
          run.id === targetRunId
            ? { ...run, status, finishedAt: new Date().toISOString() }
            : run
        )
      );
    };

    const addStep = (step: Omit<AgentStep, 'id' | 'timestamp'>) => {
      appendStep(runId, step);
    };

    const normalizeDetail = (value: unknown): string => {
      if (value === undefined || value === null) return '';
      if (typeof value === 'string') return value;
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    };

    const handleAgentEvent = (event: AgentStreamEvent) => {
      if (event.type === 'text') {
        fullContent += event.content || '';
        setStreamingContent(fullContent);
        return;
      }

      if (event.type === 'thinking') {
        addStep({
          type: 'thinking',
          title: '思考中',
          detail: event.content || '',
        });
        return;
      }

      if (event.type === 'tool_call') {
        addStep({
          type: 'tool_call',
          title: `调用工具: ${event.tool || 'unknown'}`,
          detail: normalizeDetail(event.args || {}),
        });
        return;
      }

      if (event.type === 'tool_result') {
        addStep({
          type: 'tool_result',
          title: `工具返回: ${event.tool || 'unknown'}`,
          detail: normalizeDetail(event.result || ''),
        });
        return;
      }

      if (event.type === 'metadata') {
        // Update conversation ID if this is a new conversation
        if (!conversationId && event.conversation_id && onConversationIdChange) {
          onConversationIdChange(event.conversation_id);
        }
        addStep({
          type: 'status',
          title: '执行完成',
          detail: `工具调用次数: ${event.tool_calls_count ?? 0}`,
        });
        updateRunStatus(runId, 'completed');
        // Update conversation list
        onConversationUpdate();
        return;
      }

      if (event.type === 'error') {
        fullContent += `\n\n❌ Error: ${event.content}`;
        setStreamingContent(fullContent);
        addStep({
          type: 'error',
          title: '执行异常',
          detail: event.content || 'Unknown error',
        });
        updateRunStatus(runId, 'error');
      }
    };

    addStep({
      type: 'status',
      title: 'Agent 开始执行',
      detail: '正在分析请求并准备调用工具',
    });

    await sendAgentMessage(
      {
        message: content,
        conversation_id: conversationId,
        file_context: fileContext,
        llm_config: llmConfig,
        language: language,
        agent_config: agentConfig,
      },
      handleAgentEvent
    );

    setAgentRuns((prev) =>
      prev.map((run) =>
        run.id === runId && run.status === 'running'
          ? { ...run, status: 'completed', finishedAt: new Date().toISOString() }
          : run
      )
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
    setActiveRunId(null);
  };

  const toggleRunCollapsed = (runId: number) => {
    setCollapsedRuns((prev) => ({
      ...prev,
      [runId]: !prev[runId],
    }));
  };

  const tryParseJson = (raw?: string): unknown => {
    if (!raw) return null;
    try {
      const first = JSON.parse(raw);
      if (typeof first === 'string') {
        try {
          return JSON.parse(first);
        } catch {
          return first;
        }
      }
      return first;
    } catch {
      return null;
    }
  };

  const extractMediaPreviewItems = (raw?: string): MediaPreviewItem[] => {
    const parsed = tryParseJson(raw);
    if (!parsed || typeof parsed !== 'object') return [];

    const result: MediaPreviewItem[] = [];
    const obj = parsed as Record<string, unknown>;
    const data = obj.data as Record<string, unknown> | undefined;
    const list = Array.isArray(data?.list) ? (data?.list as Array<Record<string, unknown>>) : [];

    for (const item of list) {
      const url = typeof item.url === 'string' ? item.url : '';
      if (!url) continue;

      const subtype = typeof item.subtype === 'string' ? item.subtype.toLowerCase() : '';
      const coverUrl = typeof item.cover_img === 'string' ? item.cover_img : undefined;
      const urlLower = url.toLowerCase();

      const isVideoBySubtype = subtype === 'video' || subtype === 'avatar';
      const isVideoByExt = ['.mp4', '.mov', '.webm', '.m4v', '.avi', '.mkv'].some((ext) =>
        urlLower.includes(ext)
      );
      const mediaType: 'image' | 'video' = isVideoBySubtype || isVideoByExt ? 'video' : 'image';

      result.push({
        url,
        type: mediaType,
        coverUrl,
      });
    }

    return result;
  };

  const renderStepDetail = (step: AgentStep) => {
    const mediaItems = step.type === 'tool_result' ? extractMediaPreviewItems(step.detail) : [];
    const hasMedia = mediaItems.length > 0;

    return (
      <>
        {hasMedia && (
          <div className="agent-media-grid">
            {mediaItems.map((item, index) => (
              <a
                key={`${item.url}-${index}`}
                className="agent-media-card"
                href={item.url}
                target="_blank"
                rel="noreferrer"
                title={item.url}
              >
                {item.type === 'video' ? (
                  <video
                    className="agent-media"
                    src={item.url}
                    poster={item.coverUrl}
                    muted
                    controls
                    preload="metadata"
                  />
                ) : (
                  <img className="agent-media" src={item.url} alt="generated media" loading="lazy" />
                )}
                <span className="agent-media-type">{item.type === 'video' ? 'VIDEO' : 'IMAGE'}</span>
              </a>
            ))}
          </div>
        )}
        {step.detail && (
          <details className="agent-step-raw">
            <summary>查看原始结果</summary>
            <pre className="agent-step-detail">{step.detail}</pre>
          </details>
        )}
      </>
    );
  };

  const handleFileUpload = (content: string, filename: string) => {
    setFileContext(content);
    setFileName(filename);
  };

  const handleRemoveFile = () => {
    setFileContext(null);
    setFileName(null);
  };

  const formatStepTime = (isoTime: string): string => {
    try {
      return new Date(isoTime).toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="chat-window">
      <div className="chat-content">
        {messages.length === 0 && !isLoading ? (
          <div className="welcome-message">
            <h2>欢迎来到 Emoji Studio ✨</h2>
            <p>开始对话或上传文件吧~ ✨</p>
            <div className="features">
              <div className="feature feature-chat">
                <div className="feature-icon-wrapper">
                  <div className="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="url(#gradient1)" />
                      <circle cx="8" cy="9" r="1.5" fill="white" />
                      <circle cx="12" cy="9" r="1.5" fill="white" />
                      <circle cx="16" cy="9" r="1.5" fill="white" />
                      <path d="M7 13C7 13 8.5 15 12 15C15.5 15 17 13 17 13" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                      <defs>
                        <linearGradient id="gradient1" x1="2" y1="2" x2="22" y2="22">
                          <stop offset="0%" stopColor="#ff9a9e" />
                          <stop offset="100%" stopColor="#fecfef" />
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
                      <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" fill="url(#gradient2)" />
                      <path d="M14 2V8H20" fill="url(#gradient2)" opacity="0.7" />
                      <path d="M8 12H16M8 16H13" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
                      <defs>
                        <linearGradient id="gradient2" x1="4" y1="2" x2="20" y2="22">
                          <stop offset="0%" stopColor="#a8edea" />
                          <stop offset="100%" stopColor="#fed6e3" />
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
                      <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2Z" fill="url(#gradient3)" />
                      <path d="M12 6V12L16 14" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <defs>
                        <linearGradient id="gradient3" x1="2" y1="2" x2="22" y2="22">
                          <stop offset="0%" stopColor="#ffecd2" />
                          <stop offset="100%" stopColor="#fcb69f" />
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
            <MessageList messages={messages} isLoading={isLoading && chatMode !== 'agent'} />
            {chatMode === 'agent' && agentRuns.length > 0 && (
              <div className="agent-runs-list">
                {[...agentRuns].reverse().map((run) => (
                  <div key={run.id} className="agent-live-panel">
                    <button
                      type="button"
                      className="agent-live-header"
                      onClick={() => toggleRunCollapsed(run.id)}
                      aria-expanded={!collapsedRuns[run.id]}
                    >
                      <span className={`agent-live-chevron ${collapsedRuns[run.id] ? 'collapsed' : ''}`}>
                        ▾
                      </span>
                      <span className="agent-live-title">
                        Agent 执行过程 #{run.id}
                      </span>
                      <span className={`agent-live-status agent-live-status-${run.status}`}>
                        {run.status === 'running' ? '执行中' : run.status === 'completed' ? '已完成' : '异常'}
                      </span>
                      <span className="agent-live-count">{run.steps.length} steps</span>
                    </button>
                    {!collapsedRuns[run.id] && (
                      <div className="agent-live-steps">
                        {run.steps.map((step, index) => {
                          const isLast = index === run.steps.length - 1;
                          const isRunningStep =
                            run.status === 'running' &&
                            run.id === activeRunId &&
                            isLast;

                          return (
                            <div
                              key={step.id}
                              className={`agent-timeline-step ${isRunningStep ? 'is-running' : ''}`}
                            >
                              <div className="agent-step-rail">
                                <span className={`agent-step-dot step-dot-${step.type} ${isRunningStep ? 'dot-running' : ''}`}></span>
                                {!isLast && <span className="agent-step-line"></span>}
                              </div>
                              <div className={`agent-step agent-step-${step.type}`}>
                                <div className="agent-step-title-row">
                                  <div className="agent-step-title">{step.title}</div>
                                  <div className="agent-step-meta">
                                    {isRunningStep && (
                                      <span className="agent-step-running">
                                        <span className="run-dot"></span>
                                        <span className="run-dot"></span>
                                        <span className="run-dot"></span>
                                      </span>
                                    )}
                                    <span className="agent-step-time">{formatStepTime(step.timestamp)}</span>
                                  </div>
                                </div>
                                {renderStepDetail(step)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {activeRunId && (
                  <div className="agent-live-hint">正在持续更新执行中间信息…</div>
                )}
              </div>
            )}
            {streamingContent && (
              <div className="streaming-message agent-draft-message">
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
