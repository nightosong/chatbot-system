import React, { useEffect, useMemo, useState } from 'react';
import './LanguageSettings.css';
import { languageConfigService, LanguageCode, LANGUAGE_OPTIONS } from '../services/languageConfig';
import { IconBulb, IconClose, IconGlobe, IconSettings } from './icons/AppIcons';

interface LanguageSettingsProps {
  onClose: () => void;
}

const LanguageSettings: React.FC<LanguageSettingsProps> = ({ onClose }) => {
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>('auto');

  useEffect(() => {
    const currentLanguage = languageConfigService.getLanguage();
    setSelectedLanguage(currentLanguage);
  }, []);

  const selectedOption = useMemo(
    () => LANGUAGE_OPTIONS.find((option) => option.code === selectedLanguage) || LANGUAGE_OPTIONS[0],
    [selectedLanguage]
  );

  const handleLanguageSelect = (code: LanguageCode) => {
    setSelectedLanguage(code);
    languageConfigService.setLanguage(code);
  };

  const getLanguageHint = (code: LanguageCode) => {
    if (code === 'auto') {
      return '根据你的输入语言自动切换回复语言';
    }
    return '始终使用该语言回复';
  };

  return (
    <div className="language-settings-overlay" onClick={onClose}>
      <div className="language-settings-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="language-settings-header">
          <h2 className="language-settings-title">
            <span className="language-settings-title-icon"><IconGlobe /></span>
            <span className="language-settings-title-copy">
              <span>语言设置</span>
              <small>设置 AI 回复时优先使用的语言</small>
            </span>
          </h2>
          <button className="language-settings-close" onClick={onClose}>
            <IconClose />
          </button>
        </div>

        <div className="language-settings-body">
          <div className="language-hint">
            <span className="hint-icon"><IconBulb /></span>
            <span className="hint-text">推荐保留“自动检测”，只有在你希望 AI 始终使用固定语言回复时再手动切换。</span>
          </div>

          <div className="language-current">
            <span className="language-current-label">当前选择</span>
            <div className="language-current-card">
              <span className="language-current-icon">{selectedOption.icon}</span>
              <span className="language-current-info">
                <span className="language-current-name">{selectedOption.label}</span>
                <span className="language-current-code">{selectedOption.code}</span>
              </span>
            </div>
          </div>

          <div className="language-list">
            {LANGUAGE_OPTIONS.map((option) => (
              <button
                key={option.code}
                type="button"
                className={`language-card ${selectedLanguage === option.code ? 'selected' : ''}`}
                onClick={() => handleLanguageSelect(option.code)}
              >
                <div className="language-card-main">
                  <div className="language-icon">{option.icon}</div>
                  <div className="language-info">
                    <div className="language-header-row">
                      <div className="language-label">{option.label}</div>
                      <div className="language-code">{option.code}</div>
                    </div>
                    <div className="language-hint-line">{getLanguageHint(option.code)}</div>
                  </div>
                </div>
                <div className={`selected-indicator ${selectedLanguage === option.code ? 'visible' : ''}`}>
                  <IconSettings />
                </div>
              </button>
            ))}
          </div>

          <div className="language-note">
            <span className="note-icon"><IconGlobe /></span>
            <span className="note-text">“自动检测” 会跟随你的输入语言；选择固定语言后，无论你用什么语言提问，AI 都会按该语言回复。</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LanguageSettings;
