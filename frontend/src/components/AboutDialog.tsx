import React from 'react';
import './AboutDialog.css';
import {
  IconBot,
  IconCalendar,
  IconClose,
  IconCode,
  IconCpu,
  IconFolder,
  IconGlobe,
  IconInfoCircle,
  IconMessage,
  IconSparkles,
} from './icons/AppIcons';

interface AboutDialogProps {
  onClose: () => void;
}

const AboutDialog: React.FC<AboutDialogProps> = ({ onClose }) => {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content about-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="about-header-title">
            <IconInfoCircle className="about-header-icon" />
            <span>关于</span>
          </h2>
          <button className="close-button" onClick={onClose}>
            <IconClose />
          </button>
        </div>

        <div className="modal-body about-body">
          {/* Logo 区域 */}
          <div className="about-logo">
            <div className="logo-circle">
              <div className="logo-avatar">
                <IconBot className="about-logo-icon" size={34} />
              </div>
            </div>
            <div className="logo-sparkles">
              <span className="sparkle"><IconSparkles size={16} /></span>
              <span className="sparkle"><IconSparkles size={14} /></span>
              <span className="sparkle"><IconSparkles size={12} /></span>
            </div>
          </div>

          {/* 标题 */}
          <div className="about-title">
            <h1>AI 聊天助手</h1>
            <div className="version-badge">v2.1.0</div>
          </div>

          {/* 描述 */}
          <p className="about-description">
            一个可爱的二次元风格 AI 聊天机器人 ✨
          </p>

          {/* 特性列表 */}
          <div className="about-features">
            <div className="feature-item">
              <span className="feature-icon"><IconCpu /></span>
              <div className="feature-text">
                <div className="feature-title">多模型支持</div>
                <div className="feature-desc">支持 GPT、Gemini、DeepSeek 等多个 AI 模型</div>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-icon"><IconGlobe /></span>
              <div className="feature-text">
                <div className="feature-title">多语言支持</div>
                <div className="feature-desc">支持中文、英文、日语等 8 种语言</div>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-icon"><IconFolder /></span>
              <div className="feature-text">
                <div className="feature-title">智能文件处理</div>
                <div className="feature-desc">自动摘要大文件，节省 90%+ token</div>
              </div>
            </div>

            <div className="feature-item">
              <span className="feature-icon"><IconMessage /></span>
              <div className="feature-text">
                <div className="feature-title">对话历史</div>
                <div className="feature-desc">本地持久化存储，可随时恢复</div>
              </div>
            </div>
          </div>

          {/* 技术栈 */}
          <div className="about-tech">
            <div className="tech-title">技术栈</div>
            <div className="tech-tags">
              <span className="tech-tag">React</span>
              <span className="tech-tag">TypeScript</span>
              <span className="tech-tag">FastAPI</span>
              <span className="tech-tag">Python</span>
              <span className="tech-tag">SQLite</span>
            </div>
          </div>

          {/* 底部信息 */}
          <div className="about-footer">
            <div className="footer-item">
              <span className="footer-icon"><IconCode /></span>
              <span>Made with ❤️ by Skywork Team</span>
            </div>
            <div className="footer-item">
              <span className="footer-icon"><IconCalendar /></span>
              <span>© 2026 All rights reserved</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutDialog;
