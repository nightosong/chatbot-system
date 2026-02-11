import React from 'react';
import './ConfirmDialog.css';

interface ConfirmDialogProps {
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  title,
  message,
  onConfirm,
  onCancel,
}) => {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="confirm-icon">
          <span className="icon-emoji">💭</span>
          <div className="icon-sparkles">
            <span className="sparkle">✨</span>
            <span className="sparkle">✨</span>
            <span className="sparkle">✨</span>
          </div>
        </div>
        
        <div className="confirm-content">
          <h3 className="confirm-title">{title}</h3>
          <p className="confirm-message">{message}</p>
        </div>
        
        <div className="confirm-actions">
          <button className="confirm-btn btn-cancel" onClick={onCancel}>
            <span className="btn-icon">🌸</span>
            <span className="btn-text">取消</span>
          </button>
          <button className="confirm-btn btn-confirm" onClick={onConfirm}>
            <span className="btn-icon">💕</span>
            <span className="btn-text">确定</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
