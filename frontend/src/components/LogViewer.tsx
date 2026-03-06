import React, { useCallback, useEffect, useMemo, useState } from 'react';
import './LogViewer.css';
import { getBackendLogs } from '../services/api';
import { IconBulb, IconClose, IconScroll, IconSettings } from './icons/AppIcons';

interface LogViewerProps {
  onClose: () => void;
}

const AUTO_REFRESH_MS = 5000;

const LogViewer: React.FC<LogViewerProps> = ({ onClose }) => {
  const [logs, setLogs] = useState<string[]>([]);
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
    } catch (e) {
      setError((e as any)?.response?.data?.detail || (e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, [keyword, level, lines]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) {
      return;
    }
    const timer = window.setInterval(() => {
      fetchLogs();
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [autoRefresh, fetchLogs]);

  const logText = useMemo(() => logs.join('\n'), [logs]);

  return (
    <div className="log-viewer-overlay" onClick={onClose}>
      <div className="log-viewer-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="log-viewer-header">
          <h2 className="log-viewer-title">
            <span className="log-viewer-title-icon"><IconScroll /></span>
            <span className="log-viewer-title-copy">
              <span>日志浏览</span>
              <small>查看后端日志、筛选内容并自动刷新</small>
            </span>
          </h2>
          <button className="log-viewer-close" onClick={onClose}>
            <IconClose />
          </button>
        </div>

        <div className="log-viewer-content">
          <div className="log-viewer-hint">
            <span className="log-viewer-hint-icon"><IconBulb /></span>
            <span className="log-viewer-hint-text">开启自动刷新后，日志会每 5 秒重新查询一次；关键词和级别筛选会实时参与查询。</span>
          </div>

          <div className="log-viewer-toolbar">
            <label className="log-control">
              <span className="log-control-label">行数</span>
              <select value={lines} onChange={(e) => setLines(Number(e.target.value))}>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </label>
            <label className="log-control">
              <span className="log-control-label">级别</span>
              <select value={level} onChange={(e) => setLevel(e.target.value)}>
                <option value="">全部</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </label>
            <label className="log-control log-control-keyword">
              <span className="log-control-label">关键词</span>
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                placeholder="过滤日志内容"
              />
            </label>
            <div className="log-toolbar-actions">
              <button className="log-btn" onClick={fetchLogs} disabled={isLoading}>
                {isLoading ? '加载中...' : '刷新'}
              </button>
              <button
                className={`log-btn ${autoRefresh ? 'active' : ''}`}
                onClick={() => setAutoRefresh((currentValue) => !currentValue)}
              >
                {autoRefresh ? '自动刷新：开' : '自动刷新：关'}
              </button>
            </div>
          </div>

          <div className="log-viewer-body">
            <div className="log-viewer-body-header">
              <span className="log-viewer-body-title">
                <IconSettings className="log-viewer-body-icon" />
                <span>日志内容</span>
              </span>
            </div>
            {error ? (
              <div className="log-error">读取日志失败：{error}</div>
            ) : (
              <pre className="log-content">{logText || (isLoading ? '加载中...' : '暂无日志')}</pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogViewer;
