import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import './ChatWindow.css';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import FileUpload from './FileUpload';
import { Message, ChatMode, AgentStreamEvent } from '../types';
import { sendMessage, sendAgentMessage, getConversation, persistAgentRunConfirmation } from '../services/api';
import { modelConfigService } from '../services/modelConfig';
import { languageConfigService } from '../services/languageConfig';
import { agentConfigService } from '../services/agentConfig';

interface ChatWindowProps {
  conversationId: string | null;
  onConversationUpdate: () => void;
  onConversationIdChange?: (id: string) => void;
  chatMode: ChatMode;
}

type GenerationBatchItemStatus = 'pending' | 'running' | 'completed' | 'failed';

interface GenerationBatchItem {
  id: string;
  name?: string;
  description?: string;
  prompt?: string;
  tool?: string;
  duration?: string | number;
  shotId?: number;
  roleLabel?: string;
  roleType?: 'primary' | 'support';
  media?: MediaPreviewItem | null;
  error?: string;
  referencePath?: string;
  previewPath?: string;
  status: GenerationBatchItemStatus;
}

interface GenerationBatch {
  batchType: string;
  title: string;
  uiGrouping?: string;
  parallelDisplaySupported?: boolean;
  parallelExecutionSupported?: boolean;
  sharedTool?: string;
  sharedArgs?: Record<string, unknown>;
  sharedConstraints?: Record<string, unknown>;
  items: GenerationBatchItem[];
}

interface AgentStep {
  id: number;
  type:
    | 'status'
    | 'thinking'
    | 'tool_call'
    | 'tool_result'
    | 'generation_batch'
    | 'error'
    | 'confirm'
    | 'llm_output';
  title: string;
  detail?: string;
  timestamp: string;
  actions?: ConfirmAction[];
  selectedAction?: string;
  batch?: GenerationBatch;
  toolName?: string;
}

interface AgentRun {
  id: number;
  status: 'running' | 'completed' | 'error';
  steps: AgentStep[];
  startedAt: string;
  finishedAt?: string;
  summary?: string;
  anchorTimestamp?: string;
}

interface MediaPreviewItem {
  url: string;
  type: 'image' | 'video';
  coverUrl?: string;
}

type AgentFeedItem =
  | { kind: 'message'; key: string; timestamp: string; order: number; message: Message }
  | { kind: 'run'; key: string; timestamp: string; order: number; run: AgentRun };

interface ConfirmAction {
  label: string;
  value: string;
  style?: 'primary' | 'danger' | 'neutral';
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
  const [mediaPreview, setMediaPreview] = useState<MediaPreviewItem | null>(null);
  const [previewOffset, setPreviewOffset] = useState({ x: 0, y: 0 });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stepIdRef = useRef<number>(0);
  const runIdRef = useRef<number>(0);
  const previewDragRef = useRef<{
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    dragging: boolean;
  }>({ startX: 0, startY: 0, originX: 0, originY: 0, dragging: false });
  const pendingConfirmSavesRef = useRef<
    Array<{ runStartedAt: string; stepTimestamp: string; selectedAction: string }>
  >([]);

  // Auto-scroll to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages, agentRuns]);

  useEffect(() => {
    if (mediaPreview) {
      setPreviewOffset({ x: 0, y: 0 });
    }
  }, [mediaPreview]);

  useEffect(() => {
    const handlePointerMove = (event: MouseEvent) => {
      const dragState = previewDragRef.current;
      if (!dragState.dragging) return;
      setPreviewOffset({
        x: dragState.originX + event.clientX - dragState.startX,
        y: dragState.originY + event.clientY - dragState.startY,
      });
    };

    const handlePointerUp = () => {
      previewDragRef.current.dragging = false;
    };

    window.addEventListener('mousemove', handlePointerMove);
    window.addEventListener('mouseup', handlePointerUp);

    return () => {
      window.removeEventListener('mousemove', handlePointerMove);
      window.removeEventListener('mouseup', handlePointerUp);
    };
  }, []);

  useEffect(() => {
    const flushPendingConfirmSaves = async () => {
      if (!conversationId || pendingConfirmSavesRef.current.length === 0) return;

      const pendingItems = [...pendingConfirmSavesRef.current];
      pendingConfirmSavesRef.current = [];

      for (const item of pendingItems) {
        try {
          await persistAgentRunConfirmation(conversationId, {
            run_started_at: item.runStartedAt,
            step_timestamp: item.stepTimestamp,
            selected_action: item.selectedAction,
          });
        } catch (error) {
          console.error('Failed to flush pending confirm action:', error);
          pendingConfirmSavesRef.current.push(item);
        }
      }
    };

    void flushPendingConfirmSaves();
  }, [conversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversation = async (id: string) => {
    try {
      setIsLoading(true);
      const data = await getConversation(id);
      setMessages(data.messages);

      const restoredRuns = rehydrateAgentRunsFromMessages(data.messages);
      setAgentRuns(restoredRuns);
      setActiveRunId(null);
      setCollapsedRuns(
        restoredRuns.reduce<Record<number, boolean>>((acc, run) => {
          acc[run.id] = false;
          return acc;
        }, {})
      );
      runIdRef.current = restoredRuns.reduce((max, run) => Math.max(max, run.id), 0);
      stepIdRef.current = restoredRuns.reduce(
        (max, run) => Math.max(max, ...run.steps.map((step) => step.id), 0),
        0
      );
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setIsLoading(false);
    }
  };

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
      runIdRef.current = 0;
      stepIdRef.current = 0;
    }
  }, [conversationId]);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() && !fileContext) return;

    const userMessageTimestamp = new Date().toISOString();

    // Add user message immediately
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: userMessageTimestamp,
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
        await handleAgentMessage(content, llmConfig, language, userMessageTimestamp);
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
      project_id: conversationId,
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
    const resolvedProjectId = response.project_id || response.conversation_id;
    if (!conversationId && resolvedProjectId && onConversationIdChange) {
      onConversationIdChange(resolvedProjectId);
    }

    // Update conversation list
    onConversationUpdate();
  };

  const handleAgentMessage = async (
    content: string,
    llmConfig: any,
    language: string | null,
    anchorTimestamp?: string
  ) => {
    const agentConfig = agentConfigService.getAgentConfig();

    let latestLlmSegment = '';
    let currentLlmStepId: number | null = null;
    let currentLlmText = '';
    let activeBatchStepId: number | null = null;
    let activeBatchExecutionQueue: Array<{ tool: string; itemId: string }> = [];
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
        anchorTimestamp,
      },
    ]);

    const appendStep = (
      targetRunId: number,
      step: Omit<AgentStep, 'id' | 'timestamp'>
    ): number => {
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
      return nextStep.id;
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

    const updateStepDetail = (
      targetRunId: number,
      targetStepId: number,
      detail: string
    ) => {
      setAgentRuns((prev) =>
        prev.map((run) =>
          run.id !== targetRunId
            ? run
            : {
                ...run,
                steps: run.steps.map((step) =>
                  step.id === targetStepId ? { ...step, detail } : step
                ),
              }
        )
      );
    };

    const updateGenerationBatch = (
      targetStepId: number,
      updater: (batch: GenerationBatch) => GenerationBatch
    ) => {
      setAgentRuns((prev) =>
        prev.map((run) =>
          run.id !== runId
            ? run
            : {
                ...run,
                steps: run.steps.map((step) => {
                  if (step.id !== targetStepId || !step.batch) return step;
                  return { ...step, batch: updater(step.batch) };
                }),
              }
        )
      );
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

    const getBatchItemMatch = (toolName: string, args: any): string | null => {
      if (activeBatchStepId === null) return null;
      const prompt = typeof args?.prompt === 'string' ? args.prompt.trim() : '';
      let matchedId: string | null = null;

      setAgentRuns((prev) => {
        const nextRuns = prev.map((run) => {
          if (run.id !== runId) return run;
          return {
            ...run,
            steps: run.steps.map((step) => {
              if (step.id !== activeBatchStepId || !step.batch) return step;
              const items = step.batch.items.map((item) => ({ ...item }));
              const compatibleItems = items.filter((item) => {
                if (item.status !== 'pending') return false;
                const expectedTool = item.tool || step.batch?.sharedTool;
                return !expectedTool || expectedTool === toolName;
              });
              const matched = compatibleItems.find((item) => prompt && item.prompt === prompt)
                || compatibleItems[0];
              if (!matched) return step;
              matched.status = 'running';
              matched.error = undefined;
              matchedId = matched.id;
              return {
                ...step,
                batch: {
                  ...step.batch,
                  items,
                },
              };
            }),
          };
        });
        return nextRuns;
      });

      return matchedId;
    };

    const markBatchResult = (toolName: string, rawResult: unknown): boolean => {
      if (activeBatchStepId === null || activeBatchExecutionQueue.length === 0) return false;
      const queueIndex = activeBatchExecutionQueue.findIndex((entry) => entry.tool === toolName);
      if (queueIndex < 0) return false;

      const [matchedExecution] = activeBatchExecutionQueue.splice(queueIndex, 1);
      const normalizedDetail = normalizeDetail(rawResult);
      const mediaItems = extractMediaPreviewItems(normalizedDetail);
      const primaryMedia = mediaItems[0] || null;
      const lowered = normalizedDetail.toLowerCase();
      const errorMessage =
        !primaryMedia && (lowered.includes('error') || lowered.includes('failed'))
          ? normalizedDetail
          : undefined;

      updateGenerationBatch(activeBatchStepId, (batch) => ({
        ...batch,
        items: batch.items.map((item) =>
          item.id !== matchedExecution.itemId
            ? item
            : {
                ...item,
                media: primaryMedia || item.media || null,
                status: errorMessage ? 'failed' : 'completed',
                error: errorMessage,
              }
        ),
      }));

      return true;
    };

    const flushLlmOutputStep = () => {
      if (currentLlmStepId === null) return;
      const normalized = currentLlmText.trim();
      if (normalized) {
        latestLlmSegment = normalized;
      }
      currentLlmStepId = null;
      currentLlmText = '';
    };

    const pushLlmChunk = (chunk: string) => {
      if (!chunk) return;
      const nextText = currentLlmText + chunk;
      currentLlmText = nextText;
      if (currentLlmStepId === null) {
        currentLlmStepId = appendStep(runId, {
          type: 'llm_output',
          title: 'LLM 输出',
          detail: nextText,
        });
      } else {
        updateStepDetail(runId, currentLlmStepId, nextText);
      }
    };

    const handleAgentEvent = (event: AgentStreamEvent) => {
      const isConfirmEvent =
        event.type === 'confirmation_required' || event.type === 'permission_required';

      if (event.type === 'text') {
        const chunk = event.content || '';
        pushLlmChunk(chunk);
        return;
      }

      flushLlmOutputStep();

      if (event.type === 'thinking') {
        addStep({
          type: 'thinking',
          title: '思考中',
          detail: event.content || '',
        });
        return;
      }

      if (isConfirmEvent) {
        const defaultActions: ConfirmAction[] = [
          { label: '确认执行', value: 'confirm', style: 'primary' },
          { label: '取消', value: 'cancel', style: 'danger' },
          { label: '稍后处理', value: 'defer', style: 'neutral' },
        ];
        const actions =
          Array.isArray(event.actions) && event.actions.length > 0
            ? event.actions.slice(0, 3)
            : defaultActions;
        const detail = normalizeDetail(event.detail ?? event.args ?? '');

        addStep({
          type: 'confirm',
          title: event.title || '等待确认',
          detail: event.message || event.content || '请确认是否继续执行下一步操作。',
          actions,
        });
        if (detail && detail !== '""') {
          addStep({
            type: 'status',
            title: '确认上下文',
            detail,
          });
        }
        return;
      }

      if (event.type === 'tool_call') {
        const matchedBatchItemId = getBatchItemMatch(event.tool || '', event.args || {});
        if (matchedBatchItemId) {
          activeBatchExecutionQueue.push({
            tool: event.tool || '',
            itemId: matchedBatchItemId,
          });
          return;
        }

        addStep({
          type: 'tool_call',
          title: `调用工具: ${event.tool || 'unknown'}`,
          detail: normalizeDetail(event.args || {}),
          toolName: event.tool,
        });
        return;
      }

      if (event.type === 'tool_result') {
        const normalizedDetail = normalizeDetail(event.result || '');
        const parsedBatch = extractGenerationBatch(event.result || '');
        if (parsedBatch) {
          activeBatchExecutionQueue = [];
          const stepId = appendStep(runId, {
            type: 'generation_batch',
            title: parsedBatch.title,
            detail: normalizedDetail,
            batch: parsedBatch,
            toolName: event.tool,
          });
          activeBatchStepId = stepId;
          return;
        }

        if (markBatchResult(event.tool || '', event.result || '')) {
          return;
        }

        addStep({
          type: 'tool_result',
          title: `工具返回: ${event.tool || 'unknown'}`,
          detail: normalizedDetail,
          toolName: event.tool,
        });
        return;
      }

      if (event.type === 'metadata') {
        const resolvedProjectId = event.project_id || event.conversation_id;
        if (!conversationId && resolvedProjectId && onConversationIdChange) {
          onConversationIdChange(resolvedProjectId);
        }
        addStep({
          type: 'status',
          title: '执行完成',
          detail: `工具调用次数: ${event.tool_calls_count ?? 0}`,
        });
        updateRunStatus(runId, 'completed');
        onConversationUpdate();
        return;
      }

      if (event.type === 'error') {
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
        project_id: conversationId,
        file_context: fileContext,
        llm_config: llmConfig,
        language: language,
        agent_config: agentConfig,
      },
      handleAgentEvent
    );
    flushLlmOutputStep();

    setAgentRuns((prev) =>
      prev.map((run) =>
        run.id === runId && run.status === 'running'
          ? { ...run, status: 'completed', finishedAt: new Date().toISOString() }
          : run
      )
    );

    setAgentRuns((prev) =>
      prev.map((run) =>
        run.id === runId
          ? {
              ...run,
              summary: (latestLlmSegment || '').trim(),
              finishedAt: new Date().toISOString(),
            }
          : run
      )
    );

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

  const isRecord = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null && !Array.isArray(value);

  function rehydrateAgentRunsFromMessages(conversationMessages: Message[]): AgentRun[] {
    let nextRunId = 0;

    const normalizeDetail = (value: unknown): string => {
      if (value === undefined || value === null) return '';
      if (typeof value === 'string') return value;
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    };

    const restoreRunFromPayload = (
      payload: Record<string, unknown>,
      fallbackMessage: Message
    ): AgentRun => {
      const startedAt =
        typeof payload.started_at === 'string' ? payload.started_at : fallbackMessage.timestamp;
      const finishedAt =
        typeof payload.finished_at === 'string' ? payload.finished_at : fallbackMessage.timestamp;
      const status: AgentRun['status'] =
        payload.status === 'error'
          ? 'error'
          : payload.status === 'running'
          ? 'running'
          : 'completed';
      const summary =
        typeof payload.summary === 'string' ? payload.summary.trim() : fallbackMessage.content;
      const anchorTimestamp =
        typeof payload.anchor_timestamp === 'string'
          ? payload.anchor_timestamp
          : startedAt;
      const toolCallsCount =
        typeof payload.tool_calls_count === 'number' ? payload.tool_calls_count : 0;
      const rawEvents = Array.isArray(payload.events) ? payload.events : [];
      const confirmations =
        isRecord(payload.confirmations)
          ? Object.entries(payload.confirmations).reduce<Record<string, string>>((acc, [key, value]) => {
              if (typeof value === 'string') {
                acc[key] = value;
              }
              return acc;
            }, {})
          : {};
      const startedAtMs = Date.parse(startedAt);

      let nextStepId = 0;
      const steps: AgentStep[] = [];
      let latestLlmSegment = '';
      let currentLlmStepId: number | null = null;
      let currentLlmText = '';
      let activeBatchStepId: number | null = null;
      let activeBatchExecutionQueue: Array<{ tool: string; itemId: string }> = [];

      const getReplayTimestamp = (event: Record<string, unknown>, index: number): string => {
        if (typeof event.timestamp === 'string' && event.timestamp) {
          return event.timestamp;
        }
        if (Number.isNaN(startedAtMs)) {
          return startedAt;
        }
        return new Date(startedAtMs + index).toISOString();
      };

      const appendStep = (
        step: Omit<AgentStep, 'id' | 'timestamp'>,
        timestamp: string
      ): number => {
        const nextStep: AgentStep = {
          ...step,
          id: ++nextStepId,
          timestamp,
        };
        steps.push(nextStep);
        return nextStep.id;
      };

      const updateStepDetail = (targetStepId: number, detail: string) => {
        const target = steps.find((step) => step.id === targetStepId);
        if (target) {
          target.detail = detail;
        }
      };

      const updateGenerationBatch = (
        targetStepId: number,
        updater: (batch: GenerationBatch) => GenerationBatch
      ) => {
        const target = steps.find((step) => step.id === targetStepId);
        if (target?.batch) {
          target.batch = updater(target.batch);
        }
      };

      const getBatchItemMatch = (toolName: string, args: any): string | null => {
        if (activeBatchStepId === null) return null;
        const prompt = typeof args?.prompt === 'string' ? args.prompt.trim() : '';
        const targetStep = steps.find((step) => step.id === activeBatchStepId);
        if (!targetStep?.batch) return null;

        const compatibleItems = targetStep.batch.items.filter((item) => {
          if (item.status !== 'pending') return false;
          const expectedTool = item.tool || targetStep.batch?.sharedTool;
          return !expectedTool || expectedTool === toolName;
        });
        const matched =
          compatibleItems.find((item) => prompt && item.prompt === prompt) || compatibleItems[0];
        if (!matched) return null;
        matched.status = 'running';
        matched.error = undefined;
        return matched.id;
      };

      const markBatchResult = (toolName: string, rawResult: unknown): boolean => {
        if (activeBatchStepId === null || activeBatchExecutionQueue.length === 0) return false;
        const queueIndex = activeBatchExecutionQueue.findIndex((entry) => entry.tool === toolName);
        if (queueIndex < 0) return false;

        const [matchedExecution] = activeBatchExecutionQueue.splice(queueIndex, 1);
        const normalizedDetail = normalizeDetail(rawResult);
        const mediaItems = extractMediaPreviewItems(normalizedDetail);
        const primaryMedia = mediaItems[0] || null;
        const lowered = normalizedDetail.toLowerCase();
        const errorMessage =
          !primaryMedia && (lowered.includes('error') || lowered.includes('failed'))
            ? normalizedDetail
            : undefined;

        updateGenerationBatch(activeBatchStepId, (batch) => ({
          ...batch,
          items: batch.items.map((item) =>
            item.id !== matchedExecution.itemId
              ? item
              : {
                  ...item,
                  media: primaryMedia || item.media || null,
                  status: errorMessage ? 'failed' : 'completed',
                  error: errorMessage,
                }
          ),
        }));

        return true;
      };

      const flushLlmOutputStep = () => {
        if (currentLlmStepId === null) return;
        const normalized = currentLlmText.trim();
        if (normalized) {
          latestLlmSegment = normalized;
        }
        currentLlmStepId = null;
        currentLlmText = '';
      };

      const pushLlmChunk = (chunk: string, timestamp: string) => {
        if (!chunk) return;
        const nextText = currentLlmText + chunk;
        currentLlmText = nextText;
        if (currentLlmStepId === null) {
          currentLlmStepId = appendStep(
            {
              type: 'llm_output',
              title: 'LLM 输出',
              detail: nextText,
            },
            timestamp
          );
        } else {
          updateStepDetail(currentLlmStepId, nextText);
        }
      };

      appendStep(
        {
          type: 'status',
          title: 'Agent 开始执行',
          detail: '正在分析请求并准备调用工具',
        },
        startedAt
      );

      rawEvents.forEach((rawEvent, index) => {
        if (!isRecord(rawEvent)) return;
        const event = rawEvent as Record<string, unknown>;
        const eventType = typeof event.type === 'string' ? event.type : '';
        const timestamp = getReplayTimestamp(event, index);
        const isConfirmEvent =
          eventType === 'confirmation_required' || eventType === 'permission_required';

        if (eventType === 'text') {
          pushLlmChunk(typeof event.content === 'string' ? event.content : '', timestamp);
          return;
        }

        flushLlmOutputStep();

        if (eventType === 'thinking') {
          appendStep(
            {
              type: 'thinking',
              title: '思考中',
              detail: typeof event.content === 'string' ? event.content : '',
            },
            timestamp
          );
          return;
        }

        if (isConfirmEvent) {
          const defaultActions: ConfirmAction[] = [
            { label: '确认执行', value: 'confirm', style: 'primary' },
            { label: '取消', value: 'cancel', style: 'danger' },
            { label: '稍后处理', value: 'defer', style: 'neutral' },
          ];
          const actions =
            Array.isArray(event.actions) && event.actions.length > 0
              ? (event.actions.slice(0, 3) as ConfirmAction[])
              : defaultActions;
          const detail = normalizeDetail(event.detail ?? event.args ?? '');

          appendStep(
            {
              type: 'confirm',
              title: typeof event.title === 'string' ? event.title : '等待确认',
              detail:
                typeof event.message === 'string'
                  ? event.message
                  : typeof event.content === 'string'
                  ? event.content
                  : '请确认是否继续执行下一步操作。',
              actions,
              selectedAction: confirmations[timestamp],
            },
            timestamp
          );
          if (detail && detail !== '""') {
            appendStep(
              {
                type: 'status',
                title: '确认上下文',
                detail,
              },
              timestamp
            );
          }
          return;
        }

        if (eventType === 'tool_call') {
          const toolName = typeof event.tool === 'string' ? event.tool : '';
          const matchedBatchItemId = getBatchItemMatch(toolName, event.args);
          if (matchedBatchItemId) {
            activeBatchExecutionQueue.push({
              tool: toolName,
              itemId: matchedBatchItemId,
            });
            return;
          }

          appendStep(
            {
              type: 'tool_call',
              title: `调用工具: ${toolName || 'unknown'}`,
              detail: normalizeDetail(event.args || {}),
              toolName,
            },
            timestamp
          );
          return;
        }

        if (eventType === 'tool_result') {
          const toolName = typeof event.tool === 'string' ? event.tool : '';
          const normalizedDetail = normalizeDetail(event.result || '');
          const parsedBatch = extractGenerationBatch(event.result);
          if (parsedBatch) {
            activeBatchExecutionQueue = [];
            activeBatchStepId = appendStep(
              {
                type: 'generation_batch',
                title: parsedBatch.title,
                detail: normalizedDetail,
                batch: parsedBatch,
                toolName,
              },
              timestamp
            );
            return;
          }

          if (markBatchResult(toolName, event.result)) {
            return;
          }

          appendStep(
            {
              type: 'tool_result',
              title: `工具返回: ${toolName || 'unknown'}`,
              detail: normalizedDetail,
              toolName,
            },
            timestamp
          );
          return;
        }

        if (eventType === 'metadata') {
          appendStep(
            {
              type: 'status',
              title: '执行完成',
              detail: `工具调用次数: ${typeof event.tool_calls_count === 'number' ? event.tool_calls_count : toolCallsCount}`,
            },
            timestamp
          );
          return;
        }

        if (eventType === 'error') {
          appendStep(
            {
              type: 'error',
              title: '执行异常',
              detail: typeof event.content === 'string' ? event.content : 'Unknown error',
            },
            timestamp
          );
        }
      });

      flushLlmOutputStep();

      if (!steps.some((step) => step.type === 'status' && step.title === '执行完成') && status === 'completed') {
        appendStep(
          {
            type: 'status',
            title: '执行完成',
            detail: `工具调用次数: ${toolCallsCount}`,
          },
          finishedAt
        );
      }

      if (!steps.some((step) => step.type === 'error') && status === 'error' && summary) {
        appendStep(
          {
            type: 'error',
            title: '执行异常',
            detail: summary,
          },
          finishedAt
        );
      }

      return {
        id: ++nextRunId,
        status,
        steps,
        startedAt,
        finishedAt,
        summary: latestLlmSegment || summary || undefined,
        anchorTimestamp,
      };
    };

    return conversationMessages
      .map((message) => {
        const metadata = isRecord(message.metadata) ? message.metadata : null;
        const agentRun = metadata && isRecord(metadata.agent_run) ? metadata.agent_run : null;
        if (!agentRun) return null;
        return restoreRunFromPayload(agentRun, message);
      })
      .filter((run): run is AgentRun => run !== null);
  }


  const inferMediaType = (url: string, subtype?: string): 'image' | 'video' => {
    const normalizedSubtype = (subtype || '').toLowerCase();
    const urlLower = url.toLowerCase();
    const isVideoBySubtype = normalizedSubtype === 'video' || normalizedSubtype === 'avatar';
    const isVideoByExt = ['.mp4', '.mov', '.webm', '.m4v', '.avi', '.mkv'].some((ext) =>
      urlLower.includes(ext)
    );
    return isVideoBySubtype || isVideoByExt ? 'video' : 'image';
  };

  const extractMediaPreviewItems = (raw?: unknown): MediaPreviewItem[] => {
    const parsed = typeof raw === 'string' ? tryParseJson(raw) : raw;
    const queue: unknown[] = [parsed];
    const result: MediaPreviewItem[] = [];
    const seen = new Set<string>();

    const pushMedia = (url?: string, subtype?: string, coverUrl?: string) => {
      if (!url || seen.has(url)) return;
      seen.add(url);
      result.push({
        url,
        type: inferMediaType(url, subtype),
        coverUrl,
      });
    };

    while (queue.length > 0) {
      const current = queue.shift();
      if (!current) continue;

      if (typeof current === 'string') {
        const trimmed = current.trim();
        if (trimmed.startsWith('http')) {
          pushMedia(trimmed);
        }
        continue;
      }

      if (Array.isArray(current)) {
        current.forEach((item) => queue.push(item));
        continue;
      }

      if (!isRecord(current)) continue;

      const directUrlCandidates = [
        current.url,
        current.image_url,
        current.video_url,
        current.output,
        current.cover_img,
      ];
      directUrlCandidates.forEach((candidate) => {
        if (typeof candidate === 'string' && candidate.startsWith('http')) {
          pushMedia(candidate, typeof current.subtype === 'string' ? current.subtype : undefined,
            typeof current.cover_img === 'string' ? current.cover_img : undefined);
        }
      });

      const data = current.data;
      if (isRecord(data) && Array.isArray(data.list)) {
        data.list.forEach((item) => {
          if (!isRecord(item)) return;
          const url = typeof item.url === 'string' ? item.url : '';
          const subtype = typeof item.subtype === 'string' ? item.subtype : undefined;
          const coverUrl = typeof item.cover_img === 'string' ? item.cover_img : undefined;
          pushMedia(url, subtype, coverUrl);
        });
      }

      ['result', 'content', 'items', 'generation_batch'].forEach((key) => {
        if (key in current) queue.push(current[key]);
      });
    }

    return result;
  };

  const extractGenerationBatch = (raw?: unknown): GenerationBatch | null => {
    const parsed = typeof raw === 'string' ? tryParseJson(raw) : raw;
    if (!isRecord(parsed) || !isRecord(parsed.generation_batch)) return null;

    const batchRaw = parsed.generation_batch;
    const itemsRaw = Array.isArray(batchRaw.items) ? batchRaw.items : [];
    const items = itemsRaw
      .map((item, index) => {
        if (!isRecord(item)) return null;
        const id = typeof item.id === 'string' ? item.id : `batch-item-${index + 1}`;
        const media = extractMediaPreviewItems(item)[0] || null;
        const duration =
          typeof item.duration === 'number' || typeof item.duration === 'string'
            ? item.duration
            : undefined;
        const name =
          typeof item.name === 'string'
            ? item.name
            : typeof item.shot_id === 'number'
            ? `镜头 ${item.shot_id}`
            : `任务 ${index + 1}`;

        return {
          id,
          name,
          description: typeof item.description === 'string' ? item.description : undefined,
          prompt: typeof item.prompt === 'string' ? item.prompt : undefined,
          tool: typeof item.tool === 'string' ? item.tool : undefined,
          duration,
          shotId: typeof item.shot_id === 'number' ? item.shot_id : undefined,
          roleLabel: typeof item.role_label === 'string' ? item.role_label : undefined,
          roleType:
            item.role_type === 'primary' || item.role_type === 'support'
              ? item.role_type
              : undefined,
          media,
          referencePath:
            typeof item.reference_path === 'string' ? item.reference_path : undefined,
          previewPath: typeof item.preview === 'string' ? item.preview : undefined,
          status: media ? 'completed' : 'pending',
        } as GenerationBatchItem;
      })
      .filter((item): item is GenerationBatchItem => item !== null);

    return {
      batchType: typeof batchRaw.batch_type === 'string' ? batchRaw.batch_type : 'generation',
      title: typeof batchRaw.title === 'string' ? batchRaw.title : '批量生成任务',
      uiGrouping: typeof batchRaw.ui_grouping === 'string' ? batchRaw.ui_grouping : undefined,
      parallelDisplaySupported: Boolean(batchRaw.parallel_display_supported),
      parallelExecutionSupported: Boolean(batchRaw.parallel_execution_supported),
      sharedTool: typeof batchRaw.shared_tool === 'string' ? batchRaw.shared_tool : undefined,
      sharedArgs: isRecord(batchRaw.shared_args) ? batchRaw.shared_args : undefined,
      sharedConstraints: isRecord(batchRaw.shared_constraints)
        ? batchRaw.shared_constraints
        : undefined,
      items,
    };
  };

  const getGenerationStageMeta = (batch: GenerationBatch) => {
    switch (batch.batchType) {
      case 'character_reference_images':
        return {
          stageLabel: '角色生成',
          stageHint: '统一角色风格后，集中查看角色形象结果',
        };
      case 'storyboard_images':
        return {
          stageLabel: '分镜生成',
          stageHint: '按镜头持续回填分镜图，便于整体确认节奏与构图',
        };
      case 'shot_videos':
        return {
          stageLabel: '视频生成',
          stageHint: '按镜头持续生成视频片段，完成后再决定是否合成',
        };
      default:
        return {
          stageLabel: '批量生成',
          stageHint: '批量任务正在持续更新',
        };
    }
  };

  const formatBatchToolLabel = (tool?: string): string => {
    if (tool === 'text_to_image_generation') return '文生图';
    if (tool === 'image_to_image_generation') return '图生图';
    if (tool === 'image_to_video_generation') return '图生视频';
    return tool || '工具';
  };

  const formatBatchDurationLabel = (duration?: string | number): string | null => {
    if (duration === undefined || duration === null || duration === '') return null;
    if (typeof duration === 'number') return `${duration}s`;
    return String(duration);
  };

  const startPreviewDrag = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    previewDragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      originX: previewOffset.x,
      originY: previewOffset.y,
      dragging: true,
    };
  };

  const renderMediaActionIcon = (kind: 'zoom' | 'download') => {
    if (kind === 'zoom') {
      return (
        <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="8.5" cy="8.5" r="4.75" stroke="currentColor" strokeWidth="1.6" />
          <path d="M12 12L16 16" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M8.5 6.5V10.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
          <path d="M6.5 8.5H10.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M10 3.75V11.25" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        <path d="M7.25 8.75L10 11.5L12.75 8.75" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4.75 13.25V14C4.75 14.9665 5.5335 15.75 6.5 15.75H13.5C14.4665 15.75 15.25 14.9665 15.25 14V13.25" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    );
  };

  const buildRetryMessage = (step: AgentStep, item: GenerationBatchItem): string => {
    const parsed = tryParseJson(step.detail);
    const batch = step.batch;
    const batchType = batch?.batchType || 'generation';
    const itemName = item.name || item.id;
    const prompt = item.prompt || '';
    const tool = item.tool || batch?.sharedTool || '对应生成工具';
    const styleHint =
      isRecord(parsed) && isRecord(parsed.generation_batch) && isRecord(parsed.generation_batch.shared_constraints)
        ? parsed.generation_batch.shared_constraints.style
        : undefined;
    const styleText = typeof styleHint === 'string' && styleHint ? `，保持 ${styleHint} 风格一致` : '';

    if (batchType === 'character_reference_images') {
      return `请重试生成角色形象：${itemName}。继续使用原提示词与同一视觉风格${styleText}。优先调用 ${tool}。${prompt ? `
原提示词：${prompt}` : ''}`;
    }
    if (batchType === 'storyboard_images') {
      return `请重试生成分镜图：${itemName}。保持已确认角色设计和整体画风一致${styleText}。优先调用 ${tool}。${prompt ? `
原提示词：${prompt}` : ''}`;
    }
    if (batchType === 'shot_videos') {
      return `请重试生成视频片段：${itemName}。保持与对应分镜图一致的运动和视觉风格${styleText}。优先调用 ${tool}。${prompt ? `
原提示词：${prompt}` : ''}`;
    }
    return `请重试生成任务：${itemName}。优先调用 ${tool}。${prompt ? `
原提示词：${prompt}` : ''}`;
  };

  const handleBatchItemRetry = async (step: AgentStep, item: GenerationBatchItem) => {
    if (isLoading) return;

    const retryMessage = buildRetryMessage(step, item);
    const retryTimestamp = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      {
        role: 'user',
        content: retryMessage,
        timestamp: retryTimestamp,
      },
    ]);

    const defaultModel = modelConfigService.getDefault();
    const llmConfig = defaultModel
      ? {
          provider: defaultModel.platform,
          api_key: defaultModel.apiKey,
          model_name: defaultModel.modelName,
          base_url: defaultModel.baseUrl || undefined,
        }
      : null;
    const language = languageConfigService.getLanguage();

    try {
      setIsLoading(true);
      await handleAgentMessage(retryMessage, llmConfig, language, retryTimestamp);
      onConversationUpdate();
    } catch (error) {
      console.error('Failed to retry batch item:', error);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ 重试该生成任务时出现错误，请稍后再试。',
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderBatchCard = (step: AgentStep) => {
    if (!step.batch) return null;

    const batch = step.batch;
    const { stageLabel, stageHint } = getGenerationStageMeta(batch);
    const total = batch.items.length;
    const completed = batch.items.filter((item) => item.status === 'completed').length;
    const failed = batch.items.filter((item) => item.status === 'failed').length;
    const running = batch.items.filter((item) => item.status === 'running').length;
    const progress = total > 0 ? Math.round(((completed + failed) / total) * 100) : 0;

    return (
      <div className="agent-generation-batch">
        <div className="agent-generation-batch-topbar">
          <div className="agent-generation-stage-pill">{stageLabel}</div>
          <div className="agent-generation-stage-hint">{stageHint}</div>
        </div>

        <div className="agent-generation-batch-header">
          <div className="agent-generation-batch-title-group">
            <div className="agent-generation-batch-title">{batch.title}</div>
            <div className="agent-generation-batch-meta">
              <span>{completed}/{total} 完成</span>
              {running > 0 && <span>· {running} 生成中</span>}
              {failed > 0 && <span>· {failed} 失败</span>}
              {batch.parallelDisplaySupported && <span>· 聚合展示</span>}
            </div>
          </div>
          <div className="agent-generation-batch-badges">
            {batch.sharedTool && (
              <span className="agent-generation-batch-badge">{batch.sharedTool}</span>
            )}
            {batch.parallelExecutionSupported ? (
              <span className="agent-generation-batch-badge success">并行执行</span>
            ) : (
              <span className="agent-generation-batch-badge muted">顺序执行</span>
            )}
          </div>
        </div>

        <div className="agent-generation-progress-block">
          <div className="agent-generation-progress-row">
            <span className="agent-generation-progress-label">阶段进度</span>
            <span className="agent-generation-progress-value">{progress}%</span>
          </div>
          <div className="agent-generation-progress-track">
            <div
              className="agent-generation-progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <div className="agent-generation-grid">
          {batch.items.map((item) => {
            const media = item.media || null;
            const durationLabel = formatBatchDurationLabel(item.duration);
            const toolLabel = formatBatchToolLabel(item.tool || batch.sharedTool);
            const isCharacterBatch = batch.batchType === 'character_reference_images';
            const isStoryboardBatch = batch.batchType === 'storyboard_images';
            return (
              <div key={item.id} className={`agent-generation-item status-${item.status}`}>
                <div className="agent-generation-item-head">
                  <div className="agent-generation-item-title-group">
                    <div className="agent-generation-item-title-row">
                      <div className="agent-generation-item-title-main">
                        <div className="agent-generation-item-title">{item.name || item.id}</div>
                        {isCharacterBatch && item.roleLabel && (
                          <span className={`agent-generation-role-badge ${item.roleType || 'support'}`}>
                            {item.roleLabel}
                          </span>
                        )}
                      </div>
                      <span className={`agent-generation-item-status ${item.status}`}>
                        {item.status === 'pending'
                          ? '待生成'
                          : item.status === 'running'
                          ? '生成中'
                          : item.status === 'completed'
                          ? '已完成'
                          : '失败'}
                      </span>
                    </div>
                    {isStoryboardBatch ? (
                      <div className="agent-generation-item-meta-pills">
                        {item.shotId !== undefined && (
                          <span className="agent-generation-meta-pill emphasis">镜头 {String(item.shotId).padStart(2, '0')}</span>
                        )}
                        {durationLabel && (
                          <span className="agent-generation-meta-pill">时长 {durationLabel}</span>
                        )}
                        <span className="agent-generation-meta-pill tool">{toolLabel}</span>
                      </div>
                    ) : (
                      <div className="agent-generation-item-subtitle">
                        {item.description || toolLabel || '等待生成'}
                        {durationLabel ? ` · ${durationLabel}` : ''}
                      </div>
                    )}
                  </div>
                </div>

                <div className="agent-generation-item-body">
                  <div className="agent-generation-item-preview compact">
                    {media ? (
                      media.type === 'video' ? (
                        <video
                          className="agent-generation-media"
                          src={media.url}
                          poster={media.coverUrl}
                          muted
                          playsInline
                          preload="metadata"
                        />
                      ) : (
                        <img className="agent-generation-media" src={media.url} alt={item.name || item.id} loading="lazy" />
                      )
                    ) : (
                      <div className={`agent-generation-placeholder ${item.status}`}>
                        {item.status === 'running' ? '正在生成…' : item.status === 'failed' ? '生成失败' : '等待结果'}
                      </div>
                    )}
                  </div>

                  <div className="agent-generation-item-content">
                    {item.prompt && (
                      <details className="agent-generation-prompt-details">
                        <summary>查看提示词</summary>
                        <div className="agent-generation-prompt">{item.prompt}</div>
                      </details>
                    )}

                    {item.error && <div className="agent-generation-error">{item.error}</div>}

                    <div className="agent-generation-actions compact">
                      {media && (
                        <button
                          type="button"
                          className="agent-media-action-btn primary icon-only"
                          onClick={() => setMediaPreview(media)}
                          title={media.type === 'video' ? '预览视频' : '放大图片'}
                          aria-label={media.type === 'video' ? '预览视频' : '放大图片'}
                        >
                          {renderMediaActionIcon('zoom')}
                        </button>
                      )}
                      {media && (
                        <a
                          className="agent-media-action-btn icon-only"
                          href={media.url}
                          download
                          title={media.type === 'video' ? '下载视频' : '下载图片'}
                          aria-label={media.type === 'video' ? '下载视频' : '下载图片'}
                        >
                          {renderMediaActionIcon('download')}
                        </a>
                      )}
                      <button
                        type="button"
                        className="agent-media-action-btn retry"
                        onClick={() => handleBatchItemRetry(step, item)}
                        disabled={isLoading}
                      >
                        重试
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderStepDetail = (runId: number, step: AgentStep) => {
    const mediaItems =
      step.type === 'tool_result' || step.type === 'generation_batch'
        ? extractMediaPreviewItems(step.detail)
        : [];
    const hasMedia = mediaItems.length > 0;

    if (step.type === 'confirm') {
      return (
        <div className="agent-confirm-request">
          <div className="agent-confirm-request-header">
            <span className="agent-confirm-request-badge">AI 请求你确认</span>
            <span className="agent-confirm-request-time">{formatStepTime(step.timestamp)}</span>
          </div>
          {!!step.detail && <div className="agent-confirm-request-body">{step.detail}</div>}
          <div className="agent-confirm-request-hint">确认后，Agent 将继续执行当前链路。</div>
          {step.actions && step.actions.length > 0 && (
            <div className="agent-step-actions agent-confirm-actions">
              {step.actions.slice(0, 3).map((action) => {
                const selected = step.selectedAction === action.value;
                return (
                  <button
                    key={`${step.id}-${action.value}`}
                    type="button"
                    className={`agent-step-action-btn ${action.style || 'neutral'} ${selected ? 'selected' : ''}`}
                    onClick={() => handleConfirmAction(runId, step.id, action)}
                  >
                    {selected ? `${action.label} ✓` : action.label}
                  </button>
                );
              })}
            </div>
          )}
          {step.selectedAction && (
            <div className="agent-step-selected agent-confirm-selected">
              {formatConfirmActionLabel(step.selectedAction)}
            </div>
          )}
        </div>
      );
    }

    if (step.type === 'generation_batch' && step.batch) {
      return (
        <>
          {renderBatchCard(step)}
          {step.detail && (
            <details className="agent-step-raw">
              <summary>查看原始结果</summary>
              <pre className="agent-step-detail">{step.detail}</pre>
            </details>
          )}
        </>
      );
    }

    return (
      <>
        {hasMedia && (
          <div className="agent-media-grid">
            {mediaItems.map((item, index) => (
              <div
                key={`${item.url}-${index}`}
                className="agent-media-card"
                title={item.url}
              >
                {item.type === 'video' ? (
                  <video
                    className="agent-media"
                    src={item.url}
                    poster={item.coverUrl}
                    muted
                    playsInline
                    preload="metadata"
                  />
                ) : (
                  <img className="agent-media" src={item.url} alt="generated media" loading="lazy" />
                )}
                <span className="agent-media-type">{item.type === 'video' ? 'VIDEO' : 'IMAGE'}</span>
                <div className="agent-media-actions">
                  <button
                    type="button"
                    className="agent-media-action-btn primary icon-only"
                    onClick={() => setMediaPreview(item)}
                    title={item.type === 'video' ? '预览视频' : '放大图片'}
                    aria-label={item.type === 'video' ? '预览视频' : '放大图片'}
                  >
                    {renderMediaActionIcon('zoom')}
                  </button>
                  <a
                    className="agent-media-action-btn icon-only"
                    href={item.url}
                    download
                    title={item.type === 'video' ? '下载视频' : '下载图片'}
                    aria-label={item.type === 'video' ? '下载视频' : '下载图片'}
                  >
                    {renderMediaActionIcon('download')}
                  </a>
                </div>
              </div>
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


  const formatRunTime = (isoTime?: string): string => {
    if (!isoTime) return '';
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

  const formatRunStatusLabel = (status: AgentRun['status']): string => {
    if (status === 'running') return '执行中';
    if (status === 'completed') return '已完成';
    return '异常';
  };

  const formatStepTypeLabel = (type: AgentStep['type']): string => {
    switch (type) {
      case 'status':
        return '状态';
      case 'thinking':
        return '思考';
      case 'tool_call':
        return '调用';
      case 'tool_result':
        return '结果';
      case 'generation_batch':
        return '批量';
      case 'error':
        return '异常';
      case 'confirm':
        return '确认';
      case 'llm_output':
        return '输出';
      default:
        return '步骤';
    }
  };

  const visibleMessages = messages;
  const agentConversationMessages = messages.filter((message) => message.role === 'user');
  const hasAgentFeedContent = agentConversationMessages.length > 0 || agentRuns.length > 0;

  const agentFeedItems: AgentFeedItem[] = (() => {
    if (chatMode !== 'agent') return [];

    const items: AgentFeedItem[] = [];
    const runsByAnchor = new Map<string, AgentRun[]>();
    const unanchoredRuns: AgentRun[] = [];

    agentRuns.forEach((run) => {
      const anchorKey = run.anchorTimestamp;
      if (!anchorKey) {
        unanchoredRuns.push(run);
        return;
      }

      const bucket = runsByAnchor.get(anchorKey) || [];
      bucket.push(run);
      runsByAnchor.set(anchorKey, bucket);
    });

    agentConversationMessages.forEach((message, index) => {
      items.push({
        kind: 'message',
        key: `message-${index}-${message.timestamp}`,
        timestamp: message.timestamp,
        order: index,
        message,
      });

      const anchoredRuns = runsByAnchor.get(message.timestamp) || [];
      anchoredRuns
        .sort((left, right) => left.id - right.id)
        .forEach((run, runIndex) => {
          items.push({
            kind: 'run',
            key: `run-${run.id}`,
            timestamp: run.startedAt,
            order: runIndex,
            run,
          });
        });
    });

    unanchoredRuns
      .sort((left, right) => left.id - right.id)
      .forEach((run, index) => {
        items.push({
          kind: 'run',
          key: `run-${run.id}`,
          timestamp: run.startedAt,
          order: index,
          run,
        });
      });

    return items;
  })();

  const formatConfirmActionLabel = (value?: string): string => {
    if (value === 'confirm') return '已确认执行';
    if (value === 'cancel') return '已取消执行';
    if (value === 'defer') return '已选择稍后处理';
    return `已选择: ${value || 'unknown'}`;
  };

  const closeMediaPreview = () => {
    setMediaPreview(null);
  };

  const handleConfirmAction = (runId: number, stepId: number, action: ConfirmAction) => {
    const currentRun = agentRuns.find((run) => run.id === runId) || null;
    const currentStep = currentRun?.steps.find((step) => step.id === stepId) || null;

    setAgentRuns((prev) =>
      prev.map((run) =>
        run.id === runId
          ? {
              ...run,
              steps: run.steps.map((step) =>
                step.id === stepId ? { ...step, selectedAction: action.value } : step
              ),
            }
          : run
      )
    );

    if (!currentRun || !currentStep) return;

    const payload = {
      runStartedAt: currentRun.startedAt,
      stepTimestamp: currentStep.timestamp,
      selectedAction: action.value,
    };

    if (!conversationId) {
      pendingConfirmSavesRef.current.push(payload);
      return;
    }

    void persistAgentRunConfirmation(conversationId, {
      run_started_at: payload.runStartedAt,
      step_timestamp: payload.stepTimestamp,
      selected_action: payload.selectedAction,
    }).catch((error) => {
      console.error('Failed to persist confirm action:', error);
      pendingConfirmSavesRef.current.push(payload);
    });
  };

  const formatMessageTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getAgentRunHeadline = (run: AgentRun): string => {
    if (run.status === 'running') return 'AI 正在处理你的请求';
    if (run.status === 'error') return 'AI 执行过程中出现异常';
    return run.summary?.trim() ? 'AI 已完成本轮处理' : 'AI 已完成执行';
  };

  const renderConversationMessage = (message: Message, key: string) => {
    return (
      <div key={key} className={`message ${message.role}`}>
        <div className={`message-avatar message-avatar-${message.role}`}>
          <span className="message-avatar-icon" aria-hidden="true">
            {message.role === 'user' ? (
              <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 10.1C12.0987 10.1 13.8 8.39868 13.8 6.3C13.8 4.20132 12.0987 2.5 10 2.5C7.90132 2.5 6.2 4.20132 6.2 6.3C6.2 8.39868 7.90132 10.1 10 10.1Z" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3.75 16.7C4.92 14.35 7.2 13 10 13C12.8 13 15.08 14.35 16.25 16.7" stroke="currentColor" strokeWidth="1.55" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            ) : (
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" fill="currentColor" fillOpacity="0.18" />
    <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" stroke="currentColor" strokeWidth="1.5" />
    <path d="M9 6.4L7.15 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M15 6.4L16.85 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <circle cx="10" cy="10.1" r="1.05" fill="currentColor" />
    <circle cx="14" cy="10.1" r="1.05" fill="currentColor" />
    <path d="M9.75 13.2C10.35 14 11.09 14.35 12 14.35C12.91 14.35 13.65 14 14.25 13.2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M10.15 17.8L9.1 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M13.85 17.8L14.9 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <circle cx="18.2" cy="7.2" r="1" fill="currentColor" fillOpacity="0.7" />
  </svg>
            )}
          </span>
        </div>
        <div className="message-content">
          <div className={`message-header ${message.role === 'user' ? 'message-header-user' : ''}`}>
            {message.role !== 'user' && <span className="message-role">AI</span>}
            <span className="message-time">{formatMessageTime(message.timestamp)}</span>
          </div>
          <div className="message-text">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>
      </div>
    );
  };

  const renderAgentRun = (run: AgentRun) => (
    <div key={`run-${run.id}`} className="message assistant agent-chain-message">
      <div className="message-avatar message-avatar-assistant agent-avatar">
        <span className="message-avatar-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" fill="currentColor" fillOpacity="0.18" />
            <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" stroke="currentColor" strokeWidth="1.5" />
            <path d="M9 6.4L7.15 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
            <path d="M15 6.4L16.85 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
            <circle cx="10" cy="10.1" r="1.05" fill="currentColor" />
            <circle cx="14" cy="10.1" r="1.05" fill="currentColor" />
            <path d="M9.75 13.2C10.35 14 11.09 14.35 12 14.35C12.91 14.35 13.65 14 14.25 13.2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
            <path d="M10.15 17.8L9.1 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
            <path d="M13.85 17.8L14.9 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
            <circle cx="18.2" cy="7.2" r="1" fill="currentColor" fillOpacity="0.7" />
          </svg>
        </span>
      </div>
      <div className="message-content">
        <div className="message-header agent-chain-header">
          <span className="message-role">AI</span>
          <span className="message-time">{formatMessageTime(run.startedAt)}</span>
        </div>
        <div className="agent-live-panel">
          <button
            type="button"
            className="agent-live-header"
            onClick={() => toggleRunCollapsed(run.id)}
            aria-expanded={!collapsedRuns[run.id]}
          >
            <span className={`agent-live-chevron ${collapsedRuns[run.id] ? 'collapsed' : ''}`}>
              ▾
            </span>
            <span className="agent-live-title-group">
              <span className="agent-live-title">{getAgentRunHeadline(run)}</span>
              <span className="agent-live-subtitle">
                {formatRunTime(run.startedAt)}
                {run.finishedAt ? ` — ${formatRunTime(run.finishedAt)}` : ''}
              </span>
            </span>
            <span className={`agent-live-status agent-live-status-${run.status}`}>
              {formatRunStatusLabel(run.status)}
            </span>
            <span className="agent-live-count">{run.steps.length} 步</span>
          </button>
          {!collapsedRuns[run.id] && (
            <div className="agent-live-steps">
              {run.steps.map((step, index) => {
                const isLast = index === run.steps.length - 1;
                const activeStepIndex =
                  run.status === 'running' && run.id === activeRunId
                    ? run.steps.length - 1
                    : null;
                const isRunningStep = activeStepIndex === index;
                const isCompletedStep = activeStepIndex === null ? true : index < activeStepIndex;
                const isPendingStep = activeStepIndex !== null && index > activeStepIndex;

                return (
                  <div
                    key={step.id}
                    className={`agent-timeline-step ${isRunningStep ? 'is-running' : ''} ${isCompletedStep ? 'is-completed' : ''} ${isPendingStep ? 'is-pending' : ''}`}
                  >
                    <div className="agent-step-rail">
                      <span className={`agent-step-dot step-dot-${step.type} ${isRunningStep ? 'dot-running' : ''}`}></span>
                      {!isLast && <span className="agent-step-line"></span>}
                    </div>
                    <div className={`agent-step agent-step-${step.type}`}>
                      <div className="agent-step-title-row">
                        <div className="agent-step-heading">
                          <span className="agent-step-index">{String(index + 1).padStart(2, '0')}</span>
                          <span className={`agent-step-kind kind-${step.type}`}>{formatStepTypeLabel(step.type)}</span>
                          <div className="agent-step-title">{step.title}</div>
                        </div>
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
                      {renderStepDetail(run.id, step)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {!!run.summary && (
            <div className="agent-final-message">
              <div className="agent-final-header">执行结论</div>
              <div className="agent-final-content">{run.summary}</div>
            </div>
          )}
          {run.status === 'running' && run.id === activeRunId && (
            <div className="agent-live-footer">
              <div className="agent-live-hint" role="status" aria-live="polite">
                <span className="agent-live-hint-dot"></span>
                <span>Agent 正在执行，链路会自动刷新。</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="chat-window">
      <div className="chat-content">
        {(chatMode === 'agent' ? !hasAgentFeedContent : messages.length === 0) && !isLoading ? (
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
            {chatMode === 'agent' ? (
              <div className="agent-feed-list">
                {agentFeedItems.map((item) =>
                  item.kind === 'message'
                    ? renderConversationMessage(item.message, item.key)
                    : renderAgentRun(item.run)
                )}
              </div>
            ) : (
              <MessageList messages={visibleMessages} isLoading={isLoading} />
            )}
          </>
        )}
        {mediaPreview && typeof document !== 'undefined' && createPortal(
          <div className="agent-media-preview-overlay" onClick={closeMediaPreview}>
            <div
              className="agent-media-preview-dialog"
              onClick={(event) => event.stopPropagation()}
              style={{ transform: `translate(${previewOffset.x}px, ${previewOffset.y}px)` }}
            >
              <div className="agent-media-preview-header draggable" onMouseDown={startPreviewDrag}>
                <div className="agent-media-preview-title-group">
                  <span className="agent-media-preview-title">{mediaPreview.type === 'video' ? '视频预览' : '图片预览'}</span>
                  <span className="agent-media-preview-subtitle">拖动顶部可移动预览窗口</span>
                </div>
                <div className="agent-media-preview-header-actions">
                  <a href={mediaPreview.url} download className="agent-media-preview-link">下载</a>
                  <button type="button" className="agent-media-preview-close" onClick={closeMediaPreview}>关闭</button>
                </div>
              </div>
              <div className="agent-media-preview-body">
                {mediaPreview.type === 'video' ? (
                  <video className="agent-media-preview-player" src={mediaPreview.url} poster={mediaPreview.coverUrl} controls autoPlay playsInline />
                ) : (
                  <img className="agent-media-preview-image" src={mediaPreview.url} alt="preview" />
                )}
              </div>
            </div>
          </div>,
          document.body
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        {fileName && (
          <div className="file-indicator">
            <span>📎 {fileName}</span>
            <button onClick={handleRemoveFile} className="remove-file-btn">✕</button>
          </div>
        )}
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={isLoading}
          leadingAccessory={<FileUpload onFileUpload={handleFileUpload} compact />}
        />
      </div>
    </div>
  );
};

export default ChatWindow;
