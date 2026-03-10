import React from 'react';
import './HomePage.css';
interface HomePageProps {
  onStartConversation: () => void;
  isCreatingConversation?: boolean;
}

const HomePage: React.FC<HomePageProps> = ({
  onStartConversation,
  isCreatingConversation = false,
}) => {

  return (
    <div className="home-page">
      <div className="home-page-shell">
        <section className="home-page-hero">
          <div className="home-page-hero-copy">
            <div className="home-page-badge">Emoji Studio Workspace · 持续对话空间</div>
            <h2 className="home-page-title">
              让每一次对话，
              <span className="home-page-title-accent">都能持续推进到结果</span>
            </h2>
            <p className="home-page-subtitle">
              新建会话后会立即生成唯一的 <code>conversation_id</code> 并同步到 URL，
              让你随时回到同一上下文继续完成任务。
            </p>
            <div className="home-page-actions">
              <button
                type="button"
                className="home-page-primary-btn"
                onClick={onStartConversation}
                disabled={isCreatingConversation}
              >
                {isCreatingConversation ? '正在创建…' : '新建对话'}
              </button>
              <div className="home-page-inline-note">当前系统会自动将会话地址同步到 URL</div>
            </div>
          </div>

          <div className="home-page-hero-art" aria-hidden="true">
            <div className="home-page-orb orb-one"></div>
            <div className="home-page-orb orb-two"></div>
            <div className="home-page-art-card art-card-main">
              <div className="art-card-header">
                <span className="art-card-dot dot-pink"></span>
                <span className="art-card-dot dot-yellow"></span>
                <span className="art-card-dot dot-blue"></span>
              </div>
              <div className="art-card-line line-strong"></div>
              <div className="art-card-line line-medium"></div>
              <div className="art-card-line line-soft"></div>
              <div className="art-card-pill-row">
                <span className="art-card-pill">Chat</span>
                <span className="art-card-pill">Agent</span>
                <span className="art-card-pill">Code</span>
              </div>
            </div>
            <div className="home-page-art-card art-card-float">
              <div className="art-card-mini-icon"></div>
              <div className="art-card-mini-lines">
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
};

export default HomePage;
