export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export interface Conversation {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string | null;
  file_context?: string | null;
  llm_config?: {
    provider: string;
    api_key: string;
    model_name: string;
    base_url?: string;
  } | null;
  language?: string | null;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
}

export interface ConversationDetail {
  conversation_id: string;
  messages: Message[];
}

export interface ModelConfig {
  id: string;
  platform: string;
  apiKey: string;
  modelName: string;
  enabled: boolean;
  isDefault?: boolean;
  baseUrl?: string;
}

export interface PlatformOption {
  value: string;
  label: string;
  icon: string;
}

export type ChatMode = 'chat' | 'agent';

export interface MCPServerConfig {
  url: string;
  transport?: string;
}

export interface MCPServersConfig {
  [key: string]: MCPServerConfig;
}

export interface MCPConfigWithMeta {
  mcpServers: MCPServersConfig;
  _meta?: {
    user_id?: string;
    project_id?: string;
    office_id?: string;
    trace_id?: string;
    question_id?: string;
    membership_refactor?: boolean;
    [key: string]: any;
  };
}

export interface AgentConfig {
  enable_mcp: boolean;
  enable_skills: boolean;
  mcp_servers?: MCPConfigWithMeta | null;
  max_iterations: number;
}

export interface AgentRequest {
  message: string;
  conversation_id?: string | null;
  file_context?: string | null;
  llm_config?: {
    provider: string;
    api_key: string;
    model_name: string;
    base_url?: string;
  } | null;
  language?: string | null;
  agent_config?: AgentConfig;
}

export interface AgentStreamEvent {
  type: 'text' | 'tool_call' | 'tool_result' | 'thinking' | 'error' | 'done' | 'metadata';
  content?: string;
  tool?: string;
  args?: any;
  result?: string;
  conversation_id?: string;
  tool_calls_count?: number;
}

export interface ToolCall {
  tool: string;
  args: any;
  result?: string;
}
