import React from 'react';
import './HomePage.css';
import { Conversation } from '../types';

interface HomePageProps {
  onStartConversation: () => void;
  onOpenConversation: (conversationId: string) => void;
  isCreatingConversation?: boolean;
  recentConversations: Conversation[];
}

const HomePage: React.FC<HomePageProps> = ({
  onStartConversation,
  onOpenConversation,
  isCreatingConversation = false,
  recentConversations,
}) => {
  const recentItems = recentConversations.slice(0, 3);

  return (
    <div className="home-page">
      <div className="home-page-shell">
        <section className="home-page-hero">
          <div className="home-page-hero-copy">
            <div className="home-page-badge">Emoji Studio Workspace</div>
            <h2 className="home-page-title">
              让每一次对话，
              <span className="home-page-title-accent">都成为可持续推进的工作空间</span>
            </h2>
            <p className="home-page-subtitle">
              创建一个新的会话后，系统会立即分配唯一的 <code>conversation_id</code>，并进入对应页面；
              无论刷新还是返回，都能继续停留在当前上下文中。
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

        <section className="home-page-section">
          <div className="home-page-section-header">
            <div>
              <h3>最近会话</h3>
              <p>继续你最近的上下文，而不必重新开始。</p>
            </div>
            {recentItems.length > 0 && <span>{recentItems.length} 个</span>}
          </div>
          {recentItems.length === 0 ? (
            <div className="home-page-empty">当前还没有最近会话，先创建一个新的吧。</div>
          ) : (
            <div className="home-page-recent-list">
              {recentItems.map((conversation) => (
                <button
                  key={conversation.conversation_id}
                  type="button"
                  className="home-page-recent-item"
                  onClick={() => onOpenConversation(conversation.conversation_id)}
                >
                  <span className="home-page-recent-title">{conversation.title}</span>
                  <span className="home-page-recent-meta">
                    {conversation.message_count} 条消息 · {new Date(conversation.updated_at).toLocaleDateString('zh-CN')}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default HomePage;
