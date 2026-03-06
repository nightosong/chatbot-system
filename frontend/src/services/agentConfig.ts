/**
 * Agent Configuration Service
 * Manages chat/agent mode selection and agent settings
 */

import { ChatMode, AgentConfig } from '../types';

const MODE_KEY = 'chat_mode';
const AGENT_CONFIG_KEY = 'agent_config';

class AgentConfigService {
  /**
   * Get current chat mode
   */
  getMode(): ChatMode {
    const mode = localStorage.getItem(MODE_KEY);
    return (mode === 'agent' ? 'agent' : 'chat') as ChatMode;
  }

  /**
   * Set chat mode
   */
  setMode(mode: ChatMode): void {
    localStorage.setItem(MODE_KEY, mode);
  }

  /**
   * Get agent configuration
   */
  getAgentConfig(): AgentConfig {
    const config = localStorage.getItem(AGENT_CONFIG_KEY);
    if (config) {
      try {
        return JSON.parse(config);
      } catch (e) {
        console.error('Failed to parse agent config:', e);
      }
    }
    
    // Default configuration
    return {
      enable_mcp: true,
      enable_skills: true,
      selected_skills: undefined,
      mcp_servers: null,
      max_iterations: 10,
    };
  }

  /**
   * Set agent configuration
   */
  setAgentConfig(config: AgentConfig): void {
    const configString = JSON.stringify(config);
    localStorage.setItem(AGENT_CONFIG_KEY, configString);
    console.log('Agent config saved to localStorage:', config);
    
    // 验证保存是否成功
    const saved = localStorage.getItem(AGENT_CONFIG_KEY);
    if (saved) {
      console.log('Verification: config successfully saved');
    } else {
      console.error('Verification: config save failed!');
    }
  }

  /**
   * Reset to default configuration
   */
  resetAgentConfig(): void {
    localStorage.removeItem(AGENT_CONFIG_KEY);
  }
}

export const agentConfigService = new AgentConfigService();
