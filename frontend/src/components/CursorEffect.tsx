import React, { useEffect, useRef } from 'react';
import './CursorEffect.css';

const CursorEffect: React.FC = () => {
  const cursorRef = useRef<HTMLDivElement>(null);
  const cursorDotRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // 更新主光标位置
      if (cursorRef.current) {
        cursorRef.current.style.left = `${e.clientX}px`;
        cursorRef.current.style.top = `${e.clientY}px`;
      }
      
      // 更新中心点位置（带延迟效果）
      if (cursorDotRef.current) {
        setTimeout(() => {
          if (cursorDotRef.current) {
            cursorDotRef.current.style.left = `${e.clientX}px`;
            cursorDotRef.current.style.top = `${e.clientY}px`;
          }
        }, 50);
      }
      
      // 检测悬停状态
      const target = e.target as HTMLElement;
      const isClickable = target.tagName === 'BUTTON' || 
                         target.tagName === 'A' || 
                         target.tagName === 'INPUT' ||
                         target.tagName === 'TEXTAREA' ||
                         target.closest('button') !== null ||
                         target.closest('a') !== null;
      
      if (cursorRef.current) {
        if (isClickable) {
          cursorRef.current.classList.add('cursor-hover');
        } else {
          cursorRef.current.classList.remove('cursor-hover');
        }
      }
    };

    const handleMouseDown = () => {
      if (cursorRef.current) {
        cursorRef.current.classList.add('cursor-click');
      }
    };

    const handleMouseUp = () => {
      if (cursorRef.current) {
        cursorRef.current.classList.remove('cursor-click');
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  return (
    <>
      {/* 外圈光晕 */}
      <div ref={cursorRef} className="custom-cursor">
        <div className="cursor-ring"></div>
      </div>
      
      {/* 中心可爱图标 */}
      <div ref={cursorDotRef} className="cursor-dot">
        <span className="cursor-icon">✨</span>
      </div>
    </>
  );
};

export default CursorEffect;
