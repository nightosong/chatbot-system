import { ModelConfig } from '../types';

const MODEL_CONFIG_KEY = 'modelConfigs';

export const modelConfigService = {
  // Get all model configurations
  getAll: (): ModelConfig[] => {
    try {
      const data = localStorage.getItem(MODEL_CONFIG_KEY);
      return data ? JSON.parse(data) : [];
    } catch (error) {
      console.error('Failed to load model configs:', error);
      return [];
    }
  },

  // Get enabled models only
  getEnabled: (): ModelConfig[] => {
    return modelConfigService.getAll().filter(model => model.enabled);
  },

  // Get model by ID
  getById: (id: string): ModelConfig | undefined => {
    return modelConfigService.getAll().find(model => model.id === id);
  },

  // Save all model configurations
  saveAll: (models: ModelConfig[]): void => {
    try {
      localStorage.setItem(MODEL_CONFIG_KEY, JSON.stringify(models));
    } catch (error) {
      console.error('Failed to save model configs:', error);
    }
  },

  // Add a new model
  add: (model: Omit<ModelConfig, 'id'>): ModelConfig => {
    const models = modelConfigService.getAll();
    const newModel: ModelConfig = {
      ...model,
      id: Date.now().toString(),
      // 如果是第一个模型，自动设为默认
      isDefault: models.length === 0 ? true : (model.isDefault || false),
    };
    
    // 如果新模型设为默认，取消其他模型的默认状态
    if (newModel.isDefault) {
      models.forEach(m => m.isDefault = false);
    }
    
    models.push(newModel);
    modelConfigService.saveAll(models);
    return newModel;
  },

  // Update a model
  update: (id: string, updates: Partial<ModelConfig>): boolean => {
    const models = modelConfigService.getAll();
    const index = models.findIndex(m => m.id === id);
    if (index === -1) return false;
    
    models[index] = { ...models[index], ...updates };
    modelConfigService.saveAll(models);
    return true;
  },

  // Delete a model
  delete: (id: string): boolean => {
    const models = modelConfigService.getAll();
    const filtered = models.filter(m => m.id !== id);
    if (filtered.length === models.length) return false;
    
    modelConfigService.saveAll(filtered);
    return true;
  },

  // Toggle model enabled status
  toggleEnabled: (id: string): boolean => {
    const models = modelConfigService.getAll();
    const model = models.find(m => m.id === id);
    if (!model) return false;
    
    model.enabled = !model.enabled;
    modelConfigService.saveAll(models);
    return true;
  },

  // Clear all configurations
  clear: (): void => {
    localStorage.removeItem(MODEL_CONFIG_KEY);
  },

  // Set a model as default
  setDefault: (id: string): boolean => {
    const models = modelConfigService.getAll();
    const model = models.find(m => m.id === id);
    if (!model) return false;
    
    // 取消所有模型的默认状态
    models.forEach(m => m.isDefault = false);
    // 设置当前模型为默认
    model.isDefault = true;
    
    modelConfigService.saveAll(models);
    return true;
  },

  // Get default model
  getDefault: (): ModelConfig | null => {
    const models = modelConfigService.getAll();
    return models.find(m => m.isDefault && m.enabled) || null;
  },
};
