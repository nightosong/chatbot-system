import React, { useState, KeyboardEvent } from 'react';
import './MessageInput.css';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled: boolean;
  leadingAccessory?: React.ReactNode;
}

const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled,
  leadingAccessory,
}) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
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
      <button onClick={handleSend} disabled={disabled || !message.trim()}>
        发送
      </button>
    </div>
  );
};

export default MessageInput;
