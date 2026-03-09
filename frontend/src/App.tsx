import React, { useState, useEffect } from 'react';
import './App.css';
import ChatWindow from './components/ChatWindow';
import HomePage from './components/HomePage';
import CodeWindow from './components/CodeWindow';
import ConversationList from './components/ConversationList';
import UserMenu from './components/UserMenu';
import { Conversation, ChatMode } from './types';
import { createConversation, getConversations } from './services/api';
import { agentConfigService } from './services/agentConfig';

const ACTIVE_PROJECT_STORAGE_KEY = 'chatbot-system.active-project-id';

const getConversationIdFromPath = (): string | null => {
  const match = window.location.pathname.match(/^\/conversation\/([^/]+)$/);
  return match ? decodeURIComponent(match[1]) : null;
};

const buildConversationPath = (conversationId: string | null): string => {
  if (!conversationId) return '/';
  return `/conversation/${encodeURIComponent(conversationId)}`;
};

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(
    () => getConversationIdFromPath() || localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY)
  );
  const [showHistory, setShowHistory] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>(() => agentConfigService.getMode());
  const [chatKey, setChatKey] = useState<number>(0);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      const routeConversationId = getConversationIdFromPath();
      const fallbackConversationId = localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY);
      setCurrentConversationId(routeConversationId || fallbackConversationId);
      setShowHistory(false);
      setChatKey((prev) => prev + 1);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    const routeConversationId = getConversationIdFromPath();

    if (currentConversationId) {
      localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, currentConversationId);
      if (routeConversationId !== currentConversationId) {
        window.history.replaceState({}, '', buildConversationPath(currentConversationId));
      }
      return;
    }

    localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
    if (window.location.pathname !== '/') {
      window.history.replaceState({}, '', '/');
    }
  }, [currentConversationId]);

  useEffect(() => {
    if (!currentConversationId || conversations.length === 0) return;

    const exists = conversations.some(
      (conversation) => conversation.conversation_id === currentConversationId
    );

    if (!exists) {
      localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
      window.history.replaceState({}, '', '/');
      setCurrentConversationId(null);
    }
  }, [conversations, currentConversationId]);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const handleNewChat = async () => {
    try {
      setIsCreatingConversation(true);
      const created = await createConversation({ title: '新对话' });
      const nextConversationId = created.project_id || created.conversation_id;
      setConversations((prev) => {
        const withoutDuplicate = prev.filter((item) => item.conversation_id !== nextConversationId);
        return [created, ...withoutDuplicate];
      });
      localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, nextConversationId);
      window.history.pushState({}, '', buildConversationPath(nextConversationId));
      setCurrentConversationId(nextConversationId);
      setShowHistory(false);
      setChatKey((prev) => prev + 1);
      void loadConversations();
    } catch (error) {
      console.error('Failed to create conversation:', error);
    } finally {
      setIsCreatingConversation(false);
    }
  };

  const handleSelectConversation = (conversationId: string) => {
    localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, conversationId);
    window.history.pushState({}, '', buildConversationPath(conversationId));
    setCurrentConversationId(conversationId);
    setShowHistory(false);
  };

  const handleConversationUpdate = () => {
    loadConversations();
  };

  const handleConversationIdChange = (id: string) => {
    localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, id);
    window.history.pushState({}, '', buildConversationPath(id));
    setCurrentConversationId(id);
  };

  const handleGoHome = () => {
    localStorage.removeItem(ACTIVE_PROJECT_STORAGE_KEY);
    window.history.pushState({}, '', '/');
    setCurrentConversationId(null);
    setShowHistory(false);
  };

  const handleModeChange = (mode: ChatMode) => {
    setChatMode(mode);
    agentConfigService.setMode(mode);
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-brand">
          <button type="button" className="header-home-btn" onClick={handleGoHome} title="返回首页">
            <span className="header-home-icon" aria-hidden="true">⌂</span>
            <span>首页</span>
          </button>
          <button type="button" className="header-title-btn" onClick={handleGoHome}>
            <h1>Emoji Studio ✨</h1>
          </button>
        </div>
        <div className="header-buttons">
          <div className="mode-switch">
            <button
              onClick={() => handleModeChange('chat')}
              className={`mode-btn ${chatMode === 'chat' ? 'active' : ''}`}
              title="普通对话模式"
            >
              Chat
            </button>
            <button
              onClick={() => handleModeChange('agent')}
              className={`mode-btn ${chatMode === 'agent' ? 'active' : ''}`}
              title="Agent 模式 - 支持工具调用"
            >
              Agent
            </button>
            <button
              onClick={() => handleModeChange('code')}
              className={`mode-btn ${chatMode === 'code' ? 'active' : ''}`}
              title="Code 模式 - 代码开发助手"
            >
              Code
            </button>
          </div>
          <button onClick={handleNewChat} className="new-chat-btn">
            新对话
          </button>
          <button onClick={() => setShowHistory(!showHistory)} className="history-btn">
            历史记录
          </button>
          <UserMenu />
        </div>
      </header>

      <div className="App-container">
        {showHistory && (
          <ConversationList
            conversations={conversations}
            onSelectConversation={handleSelectConversation}
            onClose={() => setShowHistory(false)}
            onUpdate={loadConversations}
          />
        )}

        {!currentConversationId ? (
          <HomePage
            onStartConversation={handleNewChat}
            onOpenConversation={handleSelectConversation}
            isCreatingConversation={isCreatingConversation}
            recentConversations={conversations.slice(0, 6)}
          />
        ) : chatMode === 'code' ? (
          <CodeWindow
            key={chatKey}
            conversationId={currentConversationId}
            onConversationUpdate={handleConversationUpdate}
            onConversationIdChange={handleConversationIdChange}
          />
        ) : (
          <ChatWindow
            key={chatKey}
            conversationId={currentConversationId}
            onConversationUpdate={handleConversationUpdate}
            onConversationIdChange={handleConversationIdChange}
            chatMode={chatMode}
          />
        )}
      </div>
    </div>
  );
}

export default App;
