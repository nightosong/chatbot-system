import React, { useState } from 'react';
import './ConversationList.css';
import { Conversation } from '../types';
import { deleteConversation } from '../services/api';
import ConfirmDialog from './ConfirmDialog';

interface ConversationListProps {
  conversations: Conversation[];
  onSelectConversation: (conversationId: string) => void;
  onClose: () => void;
  onUpdate: () => void;
}

const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  onSelectConversation,
  onClose,
  onUpdate,
}) => {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return '今天';
    if (diffDays === 2) return '昨天';
    if (diffDays <= 7) return `${diffDays - 1} 天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const handleDelete = (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation();
    setDeleteConfirm(conversationId);
  };

  const confirmDelete = async () => {
    if (!deleteConfirm) return;
    
    try {
      await deleteConversation(deleteConfirm);
      setDeleteConfirm(null);
      onUpdate();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('删除对话失败。请重试。');
    }
  };

  const cancelDelete = () => {
    setDeleteConfirm(null);
  };

  return (
    <>
      <div className="conversation-list-overlay" onClick={onClose}>
        <div className="conversation-list" onClick={(e) => e.stopPropagation()}>
          <div className="conversation-list-header">
            <h2>📚 对话历史 ✨</h2>
            <button onClick={onClose} className="close-btn">✕</button>
          </div>

          <div className="conversation-items">
            {conversations.length === 0 ? (
              <div className="no-conversations">
                <p>还没有对话记录哦~</p>
                <p className="hint">开始聊天来创建你的第一个对话吧！💕</p>
              </div>
            ) : (
              conversations.map((conv) => (
                <div
                  key={conv.conversation_id}
                  className="conversation-item"
                  onClick={() => onSelectConversation(conv.conversation_id)}
                >
                  <div className="conversation-info">
                    <div className="conversation-title">{conv.title}</div>
                    <div className="conversation-meta">
                      <span className="conversation-date">{formatDate(conv.updated_at)}</span>
                      <span className="conversation-count">
                        {conv.message_count} 条消息
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, conv.conversation_id)}
                    className="delete-btn"
                    title="删除对话"
                  >
                    <span className="delete-icon">✕</span>
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {deleteConfirm && (
        <ConfirmDialog
          title="确认删除 💭"
          message="确定要删除这个对话吗？删除后将无法恢复哦~"
          onConfirm={confirmDelete}
          onCancel={cancelDelete}
        />
      )}
    </>
  );
};

export default ConversationList;
