import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import * as api from './services/api';

// Mock API
jest.mock('./services/api');

const mockConversations = [
  {
    conversation_id: '1',
    title: 'Test Conversation',
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-01T00:00:00',
    message_count: 2,
  },
];

describe('App Component', () => {
  beforeEach(() => {
    (api.getConversations as jest.Mock).mockResolvedValue(mockConversations);
  });

  test('renders app header', () => {
    render(<App />);
    const headerElement = screen.getByText(/AI Chat System/i);
    expect(headerElement).toBeInTheDocument();
  });

  test('renders new chat button', () => {
    render(<App />);
    const newChatButton = screen.getByText(/New Chat/i);
    expect(newChatButton).toBeInTheDocument();
  });

  test('renders history button', () => {
    render(<App />);
    const historyButton = screen.getByText(/History/i);
    expect(historyButton).toBeInTheDocument();
  });

  test('loads conversations on mount', async () => {
    render(<App />);
    await waitFor(() => {
      expect(api.getConversations).toHaveBeenCalled();
    });
  });

  test('shows history panel when history button clicked', async () => {
    render(<App />);
    const historyButton = screen.getByText(/History/i);
    
    fireEvent.click(historyButton);
    
    await waitFor(() => {
      const historyPanel = screen.getByText(/Conversation History/i);
      expect(historyPanel).toBeInTheDocument();
    });
  });

  test('new chat button resets conversation', () => {
    render(<App />);
    const newChatButton = screen.getByText(/New Chat/i);
    
    fireEvent.click(newChatButton);
    
    // Should show welcome message
    expect(screen.getByText(/Welcome to AI Chat System/i)).toBeInTheDocument();
  });
});
