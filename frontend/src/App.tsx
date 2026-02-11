import React, { useState, useEffect } from 'react';
import './App.css';
import ChatWindow from './components/ChatWindow';
import ConversationList from './components/ConversationList';
import UserMenu from './components/UserMenu';
import CursorEffect from './components/CursorEffect';
import { Conversation, ChatMode } from './types';
import { getConversations } from './services/api';
import { agentConfigService } from './services/agentConfig';

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [chatMode, setChatMode] = useState<ChatMode>(() => agentConfigService.getMode());

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const handleNewChat = () => {
    setCurrentConversationId(null);
    setShowHistory(false);
  };

  const handleSelectConversation = (conversationId: string) => {
    setCurrentConversationId(conversationId);
    setShowHistory(false);
  };

  const handleConversationUpdate = () => {
    loadConversations();
  };

  const handleConversationIdChange = (id: string) => {
    setCurrentConversationId(id);
  };

  const handleModeChange = (mode: ChatMode) => {
    setChatMode(mode);
    agentConfigService.setMode(mode);
  };

  return (
    <div className="App">
      <CursorEffect />

      <header className="App-header">
        <h1>💕 AI 聊天助手 ✨</h1>
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

        <ChatWindow
          conversationId={currentConversationId}
          onConversationUpdate={handleConversationUpdate}
          onConversationIdChange={handleConversationIdChange}
          chatMode={chatMode}
        />
      </div>
    </div>
  );
}

export default App;
