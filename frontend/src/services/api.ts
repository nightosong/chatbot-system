import axios from 'axios';
import {
  ChatRequest,
  ChatResponse,
  Conversation,
  ConversationDetail,
  AgentRequest,
  AgentStreamEvent,
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
