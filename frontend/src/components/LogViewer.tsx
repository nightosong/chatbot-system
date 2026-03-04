import React, { useCallback, useEffect, useMemo, useState } from 'react';
import './LogViewer.css';
import { getBackendLogs } from '../services/api';

interface LogViewerProps {
  onClose: () => void;
}

const LogViewer: React.FC<LogViewerProps> = ({ onClose }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const [logFile, setLogFile] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lines, setLines] = useState(200);
  const [level, setLevel] = useState('');
  const [keyword, setKeyword] = useState('');

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getBackendLogs(lines, level || undefined, keyword || undefined);
      setLogs(result.lines || []);
      setLogFile(result.log_file || '');
    } catch (e) {
      setError((e as any)?.response?.data?.detail || (e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, [lines, level, keyword]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      fetchLogs();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, fetchLogs]);

  const logText = useMemo(() => logs.join('\n'), [logs]);

  return (
    <div className="log-viewer-overlay" onClick={onClose}>
      <div className="log-viewer-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="log-viewer-header">
          <h2>后端日志</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="log-viewer-toolbar">
          <label>
            行数
            <select value={lines} onChange={(e) => setLines(Number(e.target.value))}>
              <option value={100}>100</option>
              <option value={200}>200</option>
              <option value={500}>500</option>
              <option value={1000}>1000</option>
            </select>
          </label>
          <label>
            级别
            <select value={level} onChange={(e) => setLevel(e.target.value)}>
              <option value="">全部</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </label>
          <label className="keyword-field">
            关键词
            <input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="过滤日志内容"
            />
          </label>
          <button className="log-btn" onClick={fetchLogs} disabled={isLoading}>
            刷新
          </button>
          <button
            className={`log-btn ${autoRefresh ? 'active' : ''}`}
            onClick={() => setAutoRefresh((v) => !v)}
          >
            {autoRefresh ? '自动刷新开' : '自动刷新关'}
          </button>
        </div>

        <div className="log-viewer-meta">
          <span>文件：{logFile || '-'}</span>
          <span>条数：{logs.length}</span>
        </div>

        <div className="log-viewer-body">
          {error ? (
            <div className="log-error">读取日志失败：{error}</div>
          ) : (
            <pre className="log-content">{logText || (isLoading ? '加载中...' : '暂无日志')}</pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default LogViewer;
