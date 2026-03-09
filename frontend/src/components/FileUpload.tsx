import React, { useRef, useState } from 'react';
import './FileUpload.css';
import { uploadFile, FileUploadResponse } from '../services/api';

interface FileUploadProps {
  onFileUpload: (content: string, filename: string) => void;
  compact?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileUpload, compact = false }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<string | null>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validExtensions = [
      '.txt', '.md', '.pdf',
      '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
      '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v',
      '.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg',
    ];
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExtensions.includes(extension)) {
      setError('不支持的文件类型。请上传文档、图片、视频或音频文件。');
      return;
    }

    // Validate file size (20MB)
    if (file.size > 20 * 1024 * 1024) {
      setError('文件太大了。最大支持 20MB。');
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      setUploadInfo(null);

      const result: FileUploadResponse = await uploadFile(file);

      // Show processing info if file was summarized
      if (result.is_summarized) {
        const infoMessage = `文件已处理: ${result.filename} (${(result.original_length / 1024).toFixed(1)}KB → ${(result.processed_length / 1024).toFixed(1)}KB, ${result.compression_ratio} 压缩)`;
        setUploadInfo(infoMessage);
      } else {
        setUploadInfo(`文件已上传: ${result.filename} (${(result.original_length / 1024).toFixed(1)}KB)`);
      }

      onFileUpload(result.content, result.filename);

      // Reset file input after a delay
      setTimeout(() => {
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        setUploadInfo(null);
      }, 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || '文件上传失败。请重试。');
    } finally {
      setIsUploading(false);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`file-upload ${compact ? 'compact' : ''}`}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.pdf,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp4,.mov,.avi,.mkv,.webm,.m4v,.mp3,.wav,.aac,.flac,.m4a,.ogg"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      <button
        onClick={handleButtonClick}
        disabled={isUploading}
        className={`upload-btn ${isUploading ? 'is-uploading' : ''}`}
        aria-label={isUploading ? '正在上传文件' : '上传文件'}
        title={isUploading ? '正在上传文件' : '上传文件'}
      >
        {compact ? (
          <span className="upload-btn-icon" aria-hidden="true">
            <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path
                d="M12.9 5.05L7.05 10.9C5.97 11.98 5.97 13.72 7.05 14.8C8.13 15.88 9.87 15.88 10.95 14.8L16.6 9.15C18.04 7.71 18.04 5.38 16.6 3.94C15.16 2.5 12.83 2.5 11.39 3.94L5.18 10.15C3.38 11.95 3.38 14.87 5.18 16.67C6.98 18.47 9.9 18.47 11.7 16.67L16.05 12.32"
                stroke="currentColor"
                strokeWidth="1.85"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
        ) : isUploading ? (
          '⏳ 上传中...'
        ) : (
          '上传文件'
        )}
      </button>
      {error && <div className="upload-error">{error}</div>}
      {uploadInfo && <div className="upload-info">{uploadInfo}</div>}
    </div>
  );
};

export default FileUpload;
