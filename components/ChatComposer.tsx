'use client';

import { useState, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatComposerProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function ChatComposer({
  onSend,
  isLoading = false,
  placeholder = 'Type your message...',
}: ChatComposerProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-partselect-border bg-white p-4">
      <div className="flex gap-2">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          className="flex-1 px-4 py-2 border border-partselect-border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-partselect-primary disabled:bg-gray-50"
          style={{ minHeight: '44px', maxHeight: '120px' }}
        />
        
        <button
          onClick={handleSend}
          disabled={!message.trim() || isLoading}
          className="px-4 py-2 bg-partselect-primary text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>
      
      <p className="text-xs text-partselect-text-secondary mt-2">
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  );
}
