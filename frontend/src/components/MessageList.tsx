import React from 'react';
import './MessageList.css';
import { Message } from '../types';
import ReactMarkdown from 'react-markdown';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

const UserAvatarIcon = () => (
  <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path
      d="M10 10.1C12.0987 10.1 13.8 8.39868 13.8 6.3C13.8 4.20132 12.0987 2.5 10 2.5C7.90132 2.5 6.2 4.20132 6.2 6.3C6.2 8.39868 7.90132 10.1 10 10.1Z"
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M3.75 16.7C4.92 14.35 7.2 13 10 13C12.8 13 15.08 14.35 16.25 16.7"
      stroke="currentColor"
      strokeWidth="1.55"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const AssistantAvatarIcon = () => (
  <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M10 3.15V4.65" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M7.25 4.85H12.75" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" opacity="0.9" />
    <rect x="4.1" y="5.35" width="11.8" height="9.8" rx="4.2" fill="currentColor" opacity="0.12" />
    <rect x="4.1" y="5.35" width="11.8" height="9.8" rx="4.2" stroke="currentColor" strokeWidth="1.4" />
    <circle cx="7.75" cy="9.35" r="1.1" fill="currentColor" />
    <circle cx="12.25" cy="9.35" r="1.1" fill="currentColor" />
    <path d="M7.35 12.1C8 12.95 8.95 13.35 10 13.35C11.05 13.35 12 12.95 12.65 12.1" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
    <path d="M5.55 15.05V16.4" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
    <path d="M14.45 15.05V16.4" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
  </svg>
);

const MessageAvatar: React.FC<{ role: Message['role'] }> = ({ role }) => (
  <div className={`message-avatar message-avatar-${role}`}>
    <span className="message-avatar-icon">
      {role === 'user' ? <UserAvatarIcon /> : <AssistantAvatarIcon />}
    </span>
  </div>
);

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="message-list">
      {messages.map((message, index) => (
        <div key={index} className={`message ${message.role}`}>
          <MessageAvatar role={message.role} />
          <div className="message-content">
            <div className={`message-header ${message.role === 'user' ? 'message-header-user' : ''}`}>
              {message.role !== 'user' && (
                <span className="message-role">AI</span>
              )}
              <span className="message-time">{formatTime(message.timestamp)}</span>
            </div>
            <div className="message-text">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="message assistant">
          <MessageAvatar role="assistant" />
          <div className="message-content">
            <div className="message-header">
              <span className="message-role">AI</span>
            </div>
            <div className="message-text">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;
