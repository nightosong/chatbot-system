import React, { useRef, useState } from 'react';
import './FileUpload.css';
import { uploadFile, FileUploadResponse } from '../services/api';

interface FileUploadProps {
  onFileUpload: (content: string, filename: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileUpload }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadInfo, setUploadInfo] = useState<string | null>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validExtensions = ['.txt', '.md', '.pdf'];
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExtensions.includes(extension)) {
      setError('不支持的文件类型。请上传 .txt, .md 或 .pdf 文件。');
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
    <div className="file-upload">
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.pdf"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />
      <button
        onClick={handleButtonClick}
        disabled={isUploading}
        className="upload-btn"
      >
        {isUploading ? '⏳ 上传中...' : '📎 上传文件'}
      </button>
      {error && <div className="upload-error">{error}</div>}
      {uploadInfo && <div className="upload-info">{uploadInfo}</div>}
    </div>
  );
};

export default FileUpload;
