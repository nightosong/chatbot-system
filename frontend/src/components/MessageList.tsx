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
  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" fill="currentColor" fillOpacity="0.18" />
    <path d="M7.2 8.4C7.2 5.97 9.39 4 12 4C14.61 4 16.8 5.97 16.8 8.4V13.1C16.8 15.64 14.67 17.7 12 17.7C9.33 17.7 7.2 15.64 7.2 13.1V8.4Z" stroke="currentColor" strokeWidth="1.5" />
    <path d="M9 6.4L7.15 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M15 6.4L16.85 5.35" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <circle cx="10" cy="10.1" r="1.05" fill="currentColor" />
    <circle cx="14" cy="10.1" r="1.05" fill="currentColor" />
    <path d="M9.75 13.2C10.35 14 11.09 14.35 12 14.35C12.91 14.35 13.65 14 14.25 13.2" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M10.15 17.8L9.1 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <path d="M13.85 17.8L14.9 19.4" stroke="currentColor" strokeWidth="1.45" strokeLinecap="round" />
    <circle cx="18.2" cy="7.2" r="1" fill="currentColor" fillOpacity="0.7" />
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
