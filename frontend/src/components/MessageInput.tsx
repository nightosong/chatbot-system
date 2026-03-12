import React, { useState, KeyboardEvent } from 'react';
import './MessageInput.css';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled: boolean;
  isRunning?: boolean;
  isInterrupting?: boolean;
  onInterrupt?: () => void;
  leadingAccessory?: React.ReactNode;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled,
  isRunning = false,
  isInterrupting = false,
  onInterrupt,
  leadingAccessory,
}) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleActionClick = () => {
    if (isRunning) {
      onInterrupt?.();
      return;
    }
    handleSend();
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="message-input">
      <div className={`message-input-field ${leadingAccessory ? 'has-leading' : ''}`}>
        {leadingAccessory && (
          <div className="message-input-leading">{leadingAccessory}</div>
        )}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入消息... (Shift+Enter 换行)"
          disabled={disabled}
          rows={3}
        />
      </div>
      <button
        onClick={handleActionClick}
        disabled={isRunning ? isInterrupting : disabled || !message.trim()}
        className={isRunning ? (isInterrupting ? 'interrupt-button interrupting' : 'interrupt-button') : ''}
      >
        {isRunning ? (
          <span className="interrupt-button-content">
            <svg className="interrupt-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" />
            </svg>
            <span className="interrupt-label">{isInterrupting ? '中断中' : '中断'}</span>
          </span>
        ) : (
          '发送'
        )}
      </button>
    </div>
  );
};

export default MessageInput;
