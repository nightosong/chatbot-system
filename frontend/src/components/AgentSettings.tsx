import React, { useEffect, useState } from 'react';
import './AgentSettings.css';
import { agentConfigService } from '../services/agentConfig';
import { getAgentSkills, loadAgentSkill } from '../services/api';
import { AgentConfig, AgentSkill } from '../types';
import {
  IconBot,
  IconBulb,
  IconClose,
  IconCode,
  IconCpu,
  IconFolder,
  IconSettings,
  IconSparkles,
} from './icons/AppIcons';

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
  const [loadedSkills, setLoadedSkills] = useState<AgentSkill[]>([]);
  const [expandedSkillNames, setExpandedSkillNames] = useState<string[]>([]);

  const enabledSkillNames = config.selected_skills ?? loadedSkills.map((skill) => skill.name);

  useEffect(() => {
    const fetchSkills = async () => {
      try {
        const result = await getAgentSkills();
        setLoadedSkills(result.skills);
      } catch (error) {
        console.error('Failed to fetch agent skills:', error);
      }
    };
    fetchSkills();
  }, []);

  useEffect(() => {
    if (loadedSkills.length === 0 || config.selected_skills !== undefined) {
      return;
    }

    setConfig((currentConfig) => ({
      ...currentConfig,
      selected_skills: loadedSkills.map((skill) => skill.name),
    }));
  }, [config.selected_skills, loadedSkills]);

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
      const result = await loadAgentSkill(githubUrl.trim(), true);
      const refreshed = await getAgentSkills();
      setLoadedSkills(refreshed.skills);
      setConfig((currentConfig) => {
        if (currentConfig.selected_skills === undefined) {
          return currentConfig;
        }

        const existingNames = new Set(currentConfig.selected_skills);
        result.loaded_skills.forEach((name) => existingNames.add(name));
        return {
          ...currentConfig,
          selected_skills: Array.from(existingNames),
        };
      });
      
      setMessage({ 
        type: 'success', 
        text: `✓ Skill 加载成功：${result.loaded_count} 个（${result.loaded_skills.join(', ') || '无'}）`,
      });
      setGithubUrl('');
    } catch (error) {
      const errText =
        (error as any)?.response?.data?.detail ||
        (error as Error).message ||
        '未知错误';
      setMessage({ 
        type: 'error', 
        text: `❌ 加载失败: ${errText}`,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleSkill = (skillName: string) => {
    const enabledSkillNameSet = new Set(enabledSkillNames);

    if (enabledSkillNameSet.has(skillName)) {
      enabledSkillNameSet.delete(skillName);
    } else {
      enabledSkillNameSet.add(skillName);
    }

    setConfig({
      ...config,
      selected_skills: loadedSkills
        .map((skill) => skill.name)
        .filter((name) => enabledSkillNameSet.has(name)),
    });
  };

  const handleToggleSkillExpanded = (skillName: string) => {
    setExpandedSkillNames((currentNames) => (
      currentNames.includes(skillName)
        ? currentNames.filter((name) => name !== skillName)
        : [...currentNames, skillName]
    ));
  };

  return (
    <div className="agent-settings-overlay" onClick={onClose}>
      <div className="agent-settings-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="agent-settings-header">
          <h2 className="agent-settings-title">
            <span className="agent-settings-title-icon"><IconBot /></span>
            <span className="agent-settings-title-copy">
              <span>Agent 设置</span>
              <small>统一配置 MCP、Skills 与执行策略</small>
            </span>
          </h2>
          <button className="close-button" onClick={onClose}>
            <IconClose />
          </button>
        </div>

        <div className="agent-settings-content">
          <div className="agent-settings-guidance">
            <span className="guidance-icon"><IconBulb /></span>
            <span className="guidance-text">建议优先开启常用能力，再按需增加 MCP 配置和自定义 Skills。</span>
          </div>

          {/* MCP Server 配置 */}
          <section className="settings-section">
            <h3 className="section-title">
              <span className="section-title-icon"><IconCpu /></span>
              <span>MCP Server 配置</span>
            </h3>
            <div className="setting-item">
              <label className={`setting-toggle-card ${config.enable_mcp ? 'enabled' : ''}`}>
                <span className="setting-toggle-copy">
                  <span className="setting-toggle-title">启用 MCP 工具</span>
                  <span className="setting-toggle-description">启用后可连接 Model Context Protocol 工具与外部服务。</span>
                </span>
                <span className="setting-toggle-switch">
                  <input
                    type="checkbox"
                    checked={config.enable_mcp}
                    onChange={(e) => setConfig({ ...config, enable_mcp: e.target.checked })}
                  />
                  <span className="setting-toggle-slider" />
                </span>
              </label>
            </div>

            <div className="setting-item">
              <label className="setting-label-text setting-label-row">
                <span>MCP Servers 配置 (JSON)</span>
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
            <h3 className="section-title">
              <span className="section-title-icon"><IconSparkles /></span>
              <span>Skills 配置</span>
            </h3>
            <div className="setting-item">
              <label className={`setting-toggle-card ${config.enable_skills ? 'enabled' : ''}`}>
                <span className="setting-toggle-copy">
                  <span className="setting-toggle-title">启用自定义 Skills</span>
                  <span className="setting-toggle-description">启用后可加载文件操作、代码执行、数据分析等扩展能力。</span>
                </span>
                <span className="setting-toggle-switch">
                  <input
                    type="checkbox"
                    checked={config.enable_skills}
                    onChange={(e) => setConfig({ ...config, enable_skills: e.target.checked })}
                  />
                  <span className="setting-toggle-slider" />
                </span>
              </label>
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
            <h3 className="section-title">
              <span className="section-title-icon"><IconFolder /></span>
              <span>从 GitHub 加载 Skill</span>
            </h3>
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
              <p className="examples-title">
                <IconCode className="examples-title-icon" />
                <span>示例 Skill 仓库</span>
              </p>
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

            <div className="skill-examples">
              <p className="examples-title">
                <IconSettings className="examples-title-icon" />
                <span>当前已加载 Skills（{loadedSkills.length}）</span>
              </p>
              {loadedSkills.length > 0 ? (
                <ul className="loaded-skills-list">
                  {loadedSkills.map((skill) => (
                    <li
                      key={skill.name}
                      className={`loaded-skill-item ${enabledSkillNames.includes(skill.name) ? 'enabled' : ''} ${expandedSkillNames.includes(skill.name) ? 'expanded' : ''}`}
                    >
                      <div className="loaded-skill-row">
                        <div className="loaded-skill-main">
                          <div className="loaded-skill-header">
                            <span className="loaded-skill-name">{skill.name}</span>
                            <span className="loaded-skill-source">
                            {skill.source === 'builtin' ? '内置 Skill' : '动态 Skill'}
                            </span>
                          </div>
                          <button
                            type="button"
                            className="loaded-skill-expand"
                            onClick={() => handleToggleSkillExpanded(skill.name)}
                          >
                            {expandedSkillNames.includes(skill.name) ? '收起说明' : '查看说明'}
                          </button>
                        </div>
                        <label className="loaded-skill-toggle">
                          <input
                            type="checkbox"
                            checked={enabledSkillNames.includes(skill.name)}
                            onChange={() => handleToggleSkill(skill.name)}
                            disabled={!config.enable_skills}
                          />
                          <span className="loaded-skill-checkmark" />
                        </label>
                      </div>
                      {expandedSkillNames.includes(skill.name) && (
                        <div className="loaded-skill-description-wrap">
                          <p className="loaded-skill-description">{skill.description}</p>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="setting-description">暂无可用 Skill</p>
              )}
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
          <button className="reset-button" onClick={handleReset}>重置</button>
          <div className="footer-buttons">
            <button className="cancel-button" onClick={onClose}>关闭</button>
            <button className="save-button" onClick={handleSave}>保存</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentSettings;
