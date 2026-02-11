import React from 'react';
import { render, screen } from '@testing-library/react';
import MessageList from './MessageList';
import { Message } from '../types';

const mockMessages: Message[] = [
  {
    role: 'user',
    content: 'Hello',
    timestamp: '2024-01-01T12:00:00',
  },
  {
    role: 'assistant',
    content: 'Hi there!',
    timestamp: '2024-01-01T12:00:05',
  },
];

describe('MessageList Component', () => {
  test('renders messages', () => {
    render(<MessageList messages={mockMessages} isLoading={false} />);
    
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  test('displays user and assistant labels', () => {
    render(<MessageList messages={mockMessages} isLoading={false} />);
    
    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  test('shows loading indicator when isLoading is true', () => {
    render(<MessageList messages={[]} isLoading={true} />);
    
    const loadingIndicator = document.querySelector('.typing-indicator');
    expect(loadingIndicator).toBeInTheDocument();
  });

  test('does not show loading indicator when isLoading is false', () => {
    render(<MessageList messages={mockMessages} isLoading={false} />);
    
    const loadingIndicator = document.querySelector('.typing-indicator');
    expect(loadingIndicator).not.toBeInTheDocument();
  });

  test('renders empty list correctly', () => {
    const { container } = render(<MessageList messages={[]} isLoading={false} />);
    
    const messageList = container.querySelector('.message-list');
    expect(messageList).toBeInTheDocument();
    expect(messageList?.children.length).toBe(0);
  });
});
