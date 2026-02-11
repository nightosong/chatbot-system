import React, { useState } from 'react';
import './AgentSettings.css';
import { agentConfigService } from '../services/agentConfig';
import { AgentConfig } from '../types';

interface AgentSettingsProps {
  onClose: () => void;
}

const AgentSettings: React.FC<AgentSettingsProps> = ({ onClose }) => {
  const [config, setConfig] = useState<AgentConfig>(() => agentConfigService.getAgentConfig());
  const [mcpConfigText, setMcpConfigText] = useState(() => {
    const cfg = agentConfigService.getAgentConfig();
    return cfg.mcp_servers ? JSON.stringify(cfg.mcp_servers, null, 2) : '';
  });
  const [githubUrl, setGithubUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);

  const handleMcpConfigChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMcpConfigText(value);
    
    // 实时验证 JSON 格式
    if (value.trim()) {
      try {
        JSON.parse(value);
        setJsonError(null);
      } catch (err) {
        setJsonError('JSON 格式错误');
      }
    } else {
      setJsonError(null);
    }
  };

  const handleSave = () => {
    // Parse MCP config
    let mcpServers = null;
    if (mcpConfigText.trim()) {
      try {
        const parsed = JSON.parse(mcpConfigText);
        // 直接使用解析后的对象，支持新格式
        mcpServers = parsed;
        console.log('Parsed MCP servers:', mcpServers);
      } catch (e) {
        console.error('Failed to parse MCP config:', e);
        setMessage({ type: 'error', text: '❌ MCP 配置 JSON 格式错误' });
        setJsonError('JSON 格式错误，请检查语法');
        return;
      }
    }

    const finalConfig = {
      ...config,
      mcp_servers: mcpServers,
    };

    console.log('Saving agent config:', finalConfig);
    agentConfigService.setAgentConfig(finalConfig);
    
    // 更新本地状态，确保配置生效
    setConfig(finalConfig);
    
    setMessage({ type: 'success', text: '✓ 配置已保存并生效' });
    setJsonError(null);
    
    // 延迟关闭弹窗，让用户看到保存成功的提示
    setTimeout(() => {
      onClose();
    }, 800);
  };

  const handleReset = () => {
    agentConfigService.resetAgentConfig();
    const resetConfig = agentConfigService.getAgentConfig();
    setConfig(resetConfig);
    setMcpConfigText('');
    setJsonError(null);
    setMessage({ type: 'success', text: '✓ 已重置为默认配置' });
    setTimeout(() => {
      setMessage(null);
    }, 2000);
  };

  const handleLoadSkill = async () => {
    if (!githubUrl.trim()) {
      setMessage({ type: 'error', text: '❌ 请输入 GitHub URL' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      // TODO: 实现从 GitHub 加载 Skill 的逻辑
      // 这里需要后端 API 支持
      await new Promise(resolve => setTimeout(resolve, 1000)); // 模拟加载
      
      setMessage({ 
        type: 'success', 
        text: '✓ Skill 加载成功 (功能开发中)' 
      });
      setGithubUrl('');
    } catch (error) {
      setMessage({ 
        type: 'error', 
        text: '❌ 加载失败: ' + (error as Error).message 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="agent-settings-overlay" onClick={onClose}>
      <div className="agent-settings-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="agent-settings-header">
          <h2>🤖 Agent 设置</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="agent-settings-content">
          {/* MCP Server 配置 */}
          <section className="settings-section">
            <h3>🔧 MCP Server 配置</h3>
            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={config.enable_mcp}
                  onChange={(e) => setConfig({ ...config, enable_mcp: e.target.checked })}
                />
                <span>启用 MCP 工具</span>
              </label>
              <p className="setting-description">
                启用后可以使用 Model Context Protocol 工具
              </p>
            </div>

            <div className="setting-item">
              <label className="setting-label-text">
                MCP Servers 配置 (JSON)
                {jsonError && <span className="json-error-inline"> ⚠️ {jsonError}</span>}
              </label>
              <textarea
                className={`setting-textarea ${jsonError ? 'textarea-error' : ''}`}
                placeholder={`{\n  "mcpServers": {\n    "SkyVideoMCP": {\n      "url": "https://video-mcpserver-test.skywork.ai/sse",\n      "transport": "sse"\n    }\n  },\n  "_meta": {\n    "user_id": "356547686509986091",\n    "project_id": "1950846523680718848",\n    "office_id": "117"\n  }\n}`}
                value={mcpConfigText}
                onChange={handleMcpConfigChange}
                disabled={!config.enable_mcp}
                rows={14}
              />
              <p className="setting-description">
                粘贴 MCP 配置 JSON，_meta 在外层。支持多个 MCP 服务器。留空使用内置工具。
              </p>
            </div>
          </section>

          {/* Skills 配置 */}
          <section className="settings-section">
            <h3>⚡ Skills 配置</h3>
            <div className="setting-item">
              <label className="setting-label">
                <input
                  type="checkbox"
                  checked={config.enable_skills}
                  onChange={(e) => setConfig({ ...config, enable_skills: e.target.checked })}
                />
                <span>启用自定义 Skills</span>
              </label>
              <p className="setting-description">
                启用后可以使用文件操作、代码执行、数据分析等技能
              </p>
            </div>

            <div className="setting-item">
              <label className="setting-label-text">最大迭代次数</label>
              <input
                type="number"
                className="setting-input"
                min="1"
                max="20"
                value={config.max_iterations}
                onChange={(e) => setConfig({ ...config, max_iterations: parseInt(e.target.value) || 10 })}
              />
              <p className="setting-description">
                限制 Agent 调用工具的最大次数，防止无限循环
              </p>
            </div>
          </section>

          {/* GitHub Skill 加载 */}
          <section className="settings-section">
            <h3>📦 从 GitHub 加载 Skill</h3>
            <div className="setting-item">
              <label className="setting-label-text">GitHub Repository URL</label>
              <div className="github-input-group">
                <input
                  type="text"
                  className="setting-input"
                  placeholder="https://github.com/username/repo"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  disabled={isLoading}
                />
                <button
                  className="load-skill-button"
                  onClick={handleLoadSkill}
                  disabled={isLoading || !githubUrl.trim()}
                >
                  {isLoading ? '加载中...' : '加载 Skill'}
                </button>
              </div>
              <p className="setting-description">
                从 GitHub 仓库加载自定义 Skill（需要符合 Skill 规范）
              </p>
            </div>

            <div className="skill-examples">
              <p className="examples-title">示例 Skill 仓库：</p>
              <ul className="examples-list">
                <li>
                  <code>github.com/example/weather-skill</code>
                  <span className="example-desc">- 天气查询</span>
                </li>
                <li>
                  <code>github.com/example/translator-skill</code>
                  <span className="example-desc">- 多语言翻译</span>
                </li>
                <li>
                  <code>github.com/example/image-skill</code>
                  <span className="example-desc">- 图片处理</span>
                </li>
              </ul>
            </div>
          </section>

          {/* 消息提示 */}
          {message && (
            <div className={`settings-message ${message.type}`}>
              {message.text}
            </div>
          )}
        </div>

        <div className="agent-settings-footer">
          <button className="reset-button" onClick={handleReset}>
            🔄 重置默认
          </button>
          <div className="footer-buttons">
            <button className="cancel-button" onClick={onClose}>
              取消
            </button>
            <button className="save-button" onClick={handleSave}>
              💾 保存配置
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentSettings;
