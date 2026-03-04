import React, { useEffect, useRef } from 'react';
import './CursorEffect.css';

const CursorEffect: React.FC = () => {
  const cursorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const isInteractiveTarget = (target: HTMLElement | null): boolean => {
      if (!target) return false;
      return (
        target.tagName === 'BUTTON' ||
        target.tagName === 'A' ||
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.closest('button') !== null ||
        target.closest('a') !== null ||
        target.closest('[role="button"]') !== null
      );
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (cursorRef.current) {
        cursorRef.current.style.left = `${e.clientX}px`;
        cursorRef.current.style.top = `${e.clientY}px`;

        const target = e.target as HTMLElement;
        if (isInteractiveTarget(target)) {
          cursorRef.current.classList.add('cursor-hover');
        } else {
          cursorRef.current.classList.remove('cursor-hover');
        }
      }
    };

    const handleMouseDown = () => {
      cursorRef.current?.classList.add('cursor-press');
    };

    const handleMouseUp = () => {
      cursorRef.current?.classList.remove('cursor-press');
    };

    const handleMouseLeaveWindow = (e: MouseEvent) => {
      if (!e.relatedTarget) {
        cursorRef.current?.classList.add('cursor-hidden');
      }
    };

    const handleMouseEnterWindow = () => {
      cursorRef.current?.classList.remove('cursor-hidden');
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('mouseout', handleMouseLeaveWindow);
    window.addEventListener('mouseover', handleMouseEnterWindow);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('mouseout', handleMouseLeaveWindow);
      window.removeEventListener('mouseover', handleMouseEnterWindow);
    };
  }, []);

  return (
    <div ref={cursorRef} className="custom-cursor-arrow" aria-hidden="true">
      <span className="cursor-halo" />
      <svg className="cursor-arrow-svg" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 3L18.5 12.3L11.4 14.1L13.2 21L9.6 22L7.8 15L4 3Z" />
      </svg>
    </div>
  );
};

export default CursorEffect;
