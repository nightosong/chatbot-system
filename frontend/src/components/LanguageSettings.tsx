import React, { useState, useEffect } from 'react';
import './LanguageSettings.css';
import { languageConfigService, LanguageCode, LANGUAGE_OPTIONS } from '../services/languageConfig';

interface LanguageSettingsProps {
  onClose: () => void;
}

const LanguageSettings: React.FC<LanguageSettingsProps> = ({ onClose }) => {
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>('auto');

  useEffect(() => {
    const currentLanguage = languageConfigService.getLanguage();
    setSelectedLanguage(currentLanguage);
  }, []);

  const handleLanguageSelect = (code: LanguageCode) => {
    setSelectedLanguage(code);
    languageConfigService.setLanguage(code);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content language-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🌐 语言设置</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="language-hint">
            <span className="hint-icon">💡</span>
            <span className="hint-text">选择 AI 回复时使用的语言。设置后，AI 将使用您选择的语言进行回复。</span>
          </div>

          <div className="language-list">
            {LANGUAGE_OPTIONS.map((option) => (
              <div
                key={option.code}
                className={`language-card ${selectedLanguage === option.code ? 'selected' : ''}`}
                onClick={() => handleLanguageSelect(option.code)}
              >
                <div className="language-icon">{option.icon}</div>
                <div className="language-info">
                  <div className="language-label">{option.label}</div>
                  <div className="language-code">{option.code}</div>
                </div>
                {selectedLanguage === option.code && (
                  <div className="selected-indicator">✓</div>
                )}
              </div>
            ))}
          </div>

          <div className="language-note">
            <span className="note-icon">ℹ️</span>
            <span className="note-text">
              选择"自动检测"时，AI 会根据您的输入语言自动选择回复语言。
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LanguageSettings;
