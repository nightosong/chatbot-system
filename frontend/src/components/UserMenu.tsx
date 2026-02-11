import React, { useState, useRef, useEffect } from 'react';
import './UserMenu.css';
import ModelSettings from './ModelSettings';
import LanguageSettings from './LanguageSettings';
import AgentSettings from './AgentSettings';
import AboutDialog from './AboutDialog';

const UserMenu: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLanguageOpen, setIsLanguageOpen] = useState(false);
  const [isAgentSettingsOpen, setIsAgentSettingsOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    };

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

  const handleMenuToggle = () => {
    setIsMenuOpen(!isMenuOpen);
  };

  const handleSettingsClick = () => {
    setIsMenuOpen(false);
    setIsSettingsOpen(true);
  };

  const handleLanguageClick = () => {
    setIsMenuOpen(false);
    setIsLanguageOpen(true);
  };

  const handleAgentSettingsClick = () => {
    setIsMenuOpen(false);
    setIsAgentSettingsOpen(true);
  };

  const handleAboutClick = () => {
    setIsMenuOpen(false);
    setIsAboutOpen(true);
  };

  return (
    <>
      <div className="user-menu-container" ref={menuRef}>
        <button className="avatar-button" onClick={handleMenuToggle}>
          <div className="avatar">
            <div className="avatar-face">
              <div className="avatar-eyes">
                <span className="eye">•</span>
                <span className="eye">•</span>
              </div>
              <div className="avatar-mouth">ω</div>
            </div>
            <div className="avatar-sparkles">
              <span className="sparkle sparkle-1">✨</span>
              <span className="sparkle sparkle-2">💕</span>
            </div>
          </div>
        </button>

        {isMenuOpen && (
          <div className="dropdown-menu">
            <div className="menu-item" onClick={handleSettingsClick}>
              <span className="menu-icon">⚙️</span>
              <span className="menu-text">模型设置</span>
            </div>
            <div className="menu-item" onClick={handleLanguageClick}>
              <span className="menu-icon">🌐</span>
              <span className="menu-text">语言设置</span>
            </div>
            <div className="menu-item" onClick={handleAgentSettingsClick}>
              <span className="menu-icon">🤖</span>
              <span className="menu-text">Agent 设置</span>
            </div>
            <div className="menu-divider"></div>
            <div className="menu-item" onClick={handleAboutClick}>
              <span className="menu-icon">ℹ️</span>
              <span className="menu-text">关于</span>
            </div>
          </div>
        )}
      </div>

      {isSettingsOpen && (
        <ModelSettings onClose={() => setIsSettingsOpen(false)} />
      )}

      {isLanguageOpen && (
        <LanguageSettings onClose={() => setIsLanguageOpen(false)} />
      )}

      {isAgentSettingsOpen && (
        <AgentSettings onClose={() => setIsAgentSettingsOpen(false)} />
      )}

      {isAboutOpen && (
        <AboutDialog onClose={() => setIsAboutOpen(false)} />
      )}
    </>
  );
};

export default UserMenu;
