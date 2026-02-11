import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageInput from './MessageInput';

describe('MessageInput Component', () => {
  test('renders textarea and button', () => {
    const mockOnSend = jest.fn();
    render(<MessageInput onSendMessage={mockOnSend} disabled={false} />);
    
    expect(screen.getByPlaceholderText(/Type your message/i)).toBeInTheDocument();
    expect(screen.getByText(/Send/i)).toBeInTheDocument();
  });

  test('calls onSendMessage when send button clicked', () => {
    const mockOnSend = jest.fn();
    render(<MessageInput onSendMessage={mockOnSend} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText(/Type your message/i);
    const sendButton = screen.getByText(/Send/i);
    
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    fireEvent.click(sendButton);
    
    expect(mockOnSend).toHaveBeenCalledWith('Hello');
  });

  test('clears input after sending', () => {
    const mockOnSend = jest.fn();
    render(<MessageInput onSendMessage={mockOnSend} disabled={false} />);
    
    const textarea = screen.getByPlaceholderText(/Type your message/i) as HTMLTextAreaElement;
    const sendButton = screen.getByText(/Send/i);
    
    fireEvent.change(textarea, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);
    
    expect(textarea.value).toBe('');
  });

  test('does not send empty messages', () => {
    const mockOnSend = jest.fn();
    render(<MessageInput onSendMessage={mockOnSend} disabled={false} />);
    
    const sendButton = screen.getByText(/Send/i);
    fireEvent.click(sendButton);
    
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  test('disables input when disabled prop is true', () => {
    const mockOnSend = jest.fn();
    render(<MessageInput onSendMessage={mockOnSend} disabled={true} />);
    
    const textarea = screen.getByPlaceholderText(/Type your message/i);
    const sendButton = screen.getByRole('button');
    
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });
});
