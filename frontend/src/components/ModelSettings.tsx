import React, { useState, useEffect } from 'react';
import './ModelSettings.css';
import './PlatformIcons.css';
import { ModelConfig } from '../types';
import { modelConfigService } from '../services/modelConfig';
import {
  IconBulb,
  IconClose,
  IconPlus,
  IconSettings,
  IconSparkles,
  IconStar,
  IconTrash,
} from './icons/AppIcons';
import { PlatformBadge } from './icons/PlatformIcons';

interface ModelSettingsProps {
  onClose: () => void;
}

const PLATFORM_OPTIONS = [
  { value: 'openai', label: 'OpenAI GPT', icon: 'openai', baseUrl: '' },
  { value: 'gemini', label: 'Google Gemini', icon: 'gemini', baseUrl: '' },
  { value: 'skywork_router', label: 'Skywork Router', icon: 'skywork', baseUrl: 'https://gpt-us.singularity-ai.com/gpt-proxy/router/chat/completions' },
  { value: 'kimi', label: 'Moonshot Kimi', icon: 'kimi', baseUrl: 'https://api.moonshot.cn/v1' },
  { value: 'qwen', label: '阿里通义千问', icon: 'qwen', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { value: 'deepseek', label: 'DeepSeek', icon: 'deepseek', baseUrl: 'https://api.deepseek.com' },
  { value: 'claude', label: 'Anthropic Claude', icon: 'claude', baseUrl: '' },
  { value: 'doubao', label: '字节豆包', icon: 'doubao', baseUrl: '' },
];

const ModelSettings: React.FC<ModelSettingsProps> = ({ onClose }) => {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [isAddingNew, setIsAddingNew] = useState(false);
  const [newModel, setNewModel] = useState<Partial<ModelConfig>>({
    platform: 'openai',
    apiKey: '',
    modelName: '',
    enabled: true,
    baseUrl: '',
  });
  const selectedPlatformOption =
    PLATFORM_OPTIONS.find((option) => option.value === newModel.platform) || PLATFORM_OPTIONS[0];

  // Load models from service on mount
  useEffect(() => {
    const savedModels = modelConfigService.getAll();
    setModels(savedModels);
  }, []);

  const handleAddModel = () => {
    if (!newModel.platform || !newModel.apiKey || !newModel.modelName) {
      alert('请填写完整的模型信息！');
      return;
    }

    const platformOption = PLATFORM_OPTIONS.find(p => p.value === newModel.platform);

    const addedModel = modelConfigService.add({
      platform: newModel.platform!,
      apiKey: newModel.apiKey!,
      modelName: newModel.modelName!,
      enabled: newModel.enabled ?? true,
      baseUrl: platformOption?.baseUrl || '',
    });

    setModels([...models, addedModel]);
    setNewModel({
      platform: 'openai',
      apiKey: '',
      modelName: '',
      enabled: true,
      baseUrl: '',
    });
    setIsAddingNew(false);
  };

  const handleDeleteModel = (id: string) => {
    const model = models.find(m => m.id === id);
    if (!model) return;

    // 如果要删除的是默认模型，提示用户
    if (model.isDefault) {
      if (!window.confirm('⚠️ 这是当前默认模型，删除后需要重新选择默认模型。确定要删除吗？')) {
        return;
      }
    } else {
      if (!window.confirm('确定要删除这个模型配置吗？')) {
        return;
      }
    }

    modelConfigService.delete(id);
    const newModels = models.filter(m => m.id !== id);

    // 如果删除的是默认模型，且还有其他模型，自动选择第一个作为默认
    if (model.isDefault && newModels.length > 0) {
      modelConfigService.setDefault(newModels[0].id);
      newModels[0].isDefault = true;
    }

    setModels(newModels);
  };

  const handleSelectModel = (id: string) => {
    // 选中即设为默认，其他模型自动取消选中
    modelConfigService.setDefault(id);
    setModels(models.map(m => ({
      ...m,
      isDefault: m.id === id,
      enabled: m.id === id // 选中的模型启用，其他禁用
    })));
  };

  const getPlatformIcon = (platform: string) => {
    return <PlatformBadge platform={platform} />;
  };

  const getPlatformLabel = (platform: string) => {
    return PLATFORM_OPTIONS.find(p => p.value === platform)?.label || platform;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title-row">
            <IconSettings className="title-icon" />
            <span>模型设置</span>
          </h2>
          <button className="close-button" onClick={onClose}>
            <IconClose />
          </button>
        </div>

        <div className="modal-body">
          {/* 指导提示 - 只在有模型且不在添加状态时显示 */}
          {models.length > 0 && !isAddingNew && (
            <div className="model-list-guidance">
              <span className="guidance-icon"><IconBulb /></span>
              <span className="guidance-text">点击 <span className="guidance-check">✓</span> 按钮选择默认模型，只能选择一个。</span>
            </div>
          )}

          {/* Existing Models List - 添加新模型时隐藏 */}
          {!isAddingNew && (
            <div className="models-list">
              {models.length === 0 ? (
                <div className="empty-state">
                  <p className="empty-title">
                    <IconSparkles className="empty-icon" />
                    <span>还没有配置任何模型</span>
                  </p>
                  <p className="empty-hint">点击下方“添加新模型”按钮开始配置！</p>
                  <p className="empty-hint">
                    <IconBulb className="empty-hint-icon" />
                    <span>提示：选中的模型将作为默认聊天模型。</span>
                  </p>
                </div>
              ) : (
                models.map((model) => (
                  <div
                    key={model.id}
                    className={`model-card ${model.isDefault ? 'active-default' : 'inactive'}`}
                    data-platform={model.platform}
                  >
                    {model.isDefault && (
                      <span className="default-corner-icon" aria-label="默认模型">
                        <IconStar />
                      </span>
                    )}
                    <div className="model-header">
                      <div className="model-info">
                        <div className="model-icon">{getPlatformIcon(model.platform)}</div>
                        <div className="model-details">
                          <div className="model-platform">
                            {getPlatformLabel(model.platform)}
                            {model.isDefault && <span className="default-badge">默认</span>}
                          </div>
                          <div className="model-name">{model.modelName}</div>
                        </div>
                      </div>
                      <div className="model-actions">
                        {/* 互斥单选按钮 - 选中即为默认模型 */}
                        <div className="select-wrapper">
                          <button
                            className={`radio-select-button ${model.isDefault ? 'selected' : ''}`}
                            onClick={() => handleSelectModel(model.id)}
                            title={model.isDefault ? '当前默认模型' : '点击选择为默认模型'}
                          >
                            <span className="radio-dot"></span>
                          </button>
                          <span className="select-label">
                            {model.isDefault ? '默认' : '选择'}
                          </span>
                        </div>

                        {/* 删除 */}
                        <button
                          className="delete-button"
                          onClick={() => handleDeleteModel(model.id)}
                          title="删除模型"
                        >
                          <span className="delete-icon"><IconTrash /></span>
                        </button>
                      </div>
                    </div>
                    {/* API Key 显示已隐藏 */}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Add New Model Form */}
          {isAddingNew && (
            <div className="add-model-form">
              <h3>✨ 添加新模型</h3>

              <div className="form-group">
                <label>平台类型</label>
                <div className="platform-picker" aria-label="选择平台类型">
                  {PLATFORM_OPTIONS.map((option) => {
                    const isSelected = newModel.platform === option.value;

                    return (
                      <button
                        key={option.value}
                        type="button"
                        className={`platform-option-card ${isSelected ? 'selected' : ''}`}
                        onClick={() => setNewModel({ ...newModel, platform: option.value })}
                        aria-pressed={isSelected}
                      >
                        <span className="platform-option-icon">
                          <PlatformBadge platform={option.value} />
                        </span>
                        <span className="platform-option-texts">
                          <span className="platform-option-label">{option.label}</span>
                          <span className="platform-option-value">{option.value}</span>
                        </span>
                      </button>
                    );
                  })}
                </div>
                <div className="platform-picker-summary">
                  <span className="platform-picker-summary-label">当前选择</span>
                  <span className="platform-picker-summary-value">{selectedPlatformOption.label}</span>
                </div>
              </div>

              <div className="form-group">
                <label>模型名称</label>
                <input
                  type="text"
                  value={newModel.modelName}
                  onChange={(e) => setNewModel({ ...newModel, modelName: e.target.value })}
                  placeholder="例如: gpt-4, gemini-pro"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label>API Key</label>
                <input
                  type="password"
                  value={newModel.apiKey}
                  onChange={(e) => setNewModel({ ...newModel, apiKey: e.target.value })}
                  placeholder="输入你的 API Key"
                  className="form-input"
                />
              </div>

              <div className="form-actions">
                <button className="btn btn-cancel" onClick={() => setIsAddingNew(false)}>
                  取消
                </button>
                <button className="btn btn-primary" onClick={handleAddModel}>
                  添加
                </button>
              </div>
            </div>
          )}

          {/* Add Button */}
          {!isAddingNew && (
            <button className="add-model-button" onClick={() => setIsAddingNew(true)}>
              <IconPlus className="add-model-icon" />
              <span>添加新模型</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelSettings;
