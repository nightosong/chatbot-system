import React, { useState, useRef, useEffect } from 'react';
import './UserMenu.css';
import ModelSettings from './ModelSettings';
import LanguageSettings from './LanguageSettings';
import AgentSettings from './AgentSettings';
import AboutDialog from './AboutDialog';
import LogViewer from './LogViewer';
import {
  IconBot,
  IconGlobe,
  IconInfoCircle,
  IconScroll,
  IconSettings,
  IconUserCircle,
} from './icons/AppIcons';

const UserMenu: React.FC = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isLanguageOpen, setIsLanguageOpen] = useState(false);
  const [isAgentSettingsOpen, setIsAgentSettingsOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isLogViewerOpen, setIsLogViewerOpen] = useState(false);
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

  const handleLogViewerClick = () => {
    setIsMenuOpen(false);
    setIsLogViewerOpen(true);
  };

  return (
    <>
      <div className="user-menu-container" ref={menuRef}>
        <button className="avatar-button" onClick={handleMenuToggle}>
          <div className="avatar">
            <IconUserCircle className="avatar-icon" size={26} />
          </div>
        </button>

        {isMenuOpen && (
          <div className="dropdown-menu">
            <div className="menu-item" onClick={handleSettingsClick}>
              <span className="menu-icon"><IconSettings /></span>
              <span className="menu-text">模型设置</span>
            </div>
            <div className="menu-item" onClick={handleLanguageClick}>
              <span className="menu-icon"><IconGlobe /></span>
              <span className="menu-text">语言设置</span>
            </div>
            <div className="menu-item" onClick={handleAgentSettingsClick}>
              <span className="menu-icon"><IconBot /></span>
              <span className="menu-text">Agent 设置</span>
            </div>
            <div className="menu-item" onClick={handleLogViewerClick}>
              <span className="menu-icon"><IconScroll /></span>
              <span className="menu-text">日志浏览</span>
            </div>
            <div className="menu-divider"></div>
            <div className="menu-item" onClick={handleAboutClick}>
              <span className="menu-icon"><IconInfoCircle /></span>
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

      {isLogViewerOpen && (
        <LogViewer onClose={() => setIsLogViewerOpen(false)} />
      )}
    </>
  );
};

export default UserMenu;
