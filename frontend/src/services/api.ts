import axios from 'axios';
import {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationDetail,
  CreateConversationRequest,
  CreateConversationResponse,
  AgentRequest,
  AgentStreamEvent,
  AgentRunStartResponse,
  AgentRunStatusResponse,
  AgentSkill,
  BackendLogsResponse,
  SkillLoadResponse,
  CodeRequest,
  CodeStreamEvent,
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/api/chat', request);
  return response.data;
};

/**
 * Send message in agent mode with streaming
 * @param request Agent request
 * @param onEvent Callback for each SSE event
 * @returns Promise that resolves when stream is complete
 */
export const sendAgentMessage = async (
  request: AgentRequest,
  onEvent: (event: AgentStreamEvent) => void
): Promise<void> => {
  const start = await api.post<AgentRunStartResponse>('/api/agent/runs/start', request);
  const runId = start.data.run_id;
  await streamAgentRun(runId, onEvent);
};

export const startAgentRun = async (
  request: AgentRequest
): Promise<AgentRunStartResponse> => {
  const response = await api.post<AgentRunStartResponse>('/api/agent/runs/start', request);
  return response.data;
};

export const getAgentRun = async (runId: string): Promise<AgentRunStatusResponse> => {
  const response = await api.get<AgentRunStatusResponse>(`/api/agent/runs/${runId}`);
  return response.data;
};

export const interruptAgentRun = async (
  runId: string
): Promise<{ run_id: string; status: string; interrupt_requested: boolean }> => {
  const response = await api.post<{ run_id: string; status: string; interrupt_requested: boolean }>(
    `/api/agent/runs/${runId}/interrupt`
  );
  return response.data;
};

export const streamAgentRun = async (
  runId: string,
  onEvent: (event: AgentStreamEvent) => void,
  afterSeq?: number
): Promise<void> => {
  const searchParams = new URLSearchParams();
  if (typeof afterSeq === 'number' && afterSeq >= 0) {
    searchParams.set('after_seq', String(afterSeq));
  }
  const query = searchParams.toString();
  const response = await fetch(
    `${API_BASE_URL}/api/agent/runs/${runId}/stream${query ? `?${query}` : ''}`,
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
            
            // Stop if done
            if (data.type === 'done') {
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, line);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

export const sendAgentMessageLegacy = async (
  request: AgentRequest,
  onEvent: (event: AgentStreamEvent) => void
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/agent/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);
            
            // Stop if done
            if (data.type === 'done') {
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, line);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

export const loadAgentSkill = async (
  source: string,
  forceUpdate: boolean = false
): Promise<SkillLoadResponse> => {
  const response = await api.post<SkillLoadResponse>('/api/agent/skills/load', {
    source,
    force_update: forceUpdate,
  });
  return response.data;
};

export const getAgentSkills = async (): Promise<{ skills: AgentSkill[]; count: number }> => {
  const response = await api.get<{ skills: AgentSkill[]; count: number }>('/api/agent/skills');
  return response.data;
};

export const getBackendLogs = async (
  lines: number = 200,
  level?: string,
  contains?: string
): Promise<BackendLogsResponse> => {
  const response = await api.get<BackendLogsResponse>('/api/logs', {
    params: {
      lines,
      level: level || undefined,
      contains: contains || undefined,
    },
  });
  return response.data;
};

export interface FileUploadResponse {
  filename: string;
  content: string;
  original_length: number;
  processed_length: number;
  is_summarized: boolean;
  processing_strategy: string;
  compression_ratio: string;
}

export const uploadFile = async (file: File): Promise<FileUploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<FileUploadResponse>('/api/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const createConversation = async (
  request: CreateConversationRequest = {}
): Promise<CreateConversationResponse> => {
  const response = await api.post<CreateConversationResponse>('/api/conversations', request);
  return response.data;
};

export const getConversations = async (): Promise<Conversation[]> => {
  const response = await api.get<Conversation[]>('/api/conversations');
  return response.data;
};

export const getConversation = async (conversationId: string): Promise<ConversationDetail> => {
  const response = await api.get<ConversationDetail>(`/api/conversations/${conversationId}`);
  return response.data;
};

export const deleteConversation = async (conversationId: string): Promise<void> => {
  await api.delete(`/api/conversations/${conversationId}`);
};

export const persistAgentRunConfirmation = async (
  conversationId: string,
  request: {
    run_started_at: string;
    step_timestamp: string;
    selected_action: string;
  }
): Promise<void> => {
  await api.post(`/api/conversations/${conversationId}/agent-runs/confirm`, request);
};

/**
 * Send message in code mode with streaming
 * @param request Code request
 * @param onEvent Callback for each SSE event
 * @returns Promise that resolves when stream is complete
 */
export const sendCodeMessage = async (
  request: CodeRequest,
  onEvent: (event: CodeStreamEvent) => void
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/code/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(data);

            // Stop if done
            if (data.type === 'done') {
              return;
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, line);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

/**
 * Get available code tools
 * @returns Promise with tools list
 */
export const getCodeTools = async (): Promise<any> => {
  const response = await api.get('/api/code/tools');
  return response.data;
};
