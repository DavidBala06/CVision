import React, { useState, useRef, useEffect } from 'react';
import './AiAssistant.css';
import type { ChatMessage } from '../App';

interface AiAssistantProps {
  onSendMessage: (query: string) => void;
  messages: ChatMessage[];
  isLoading: boolean;
}

const AiAssistant: React.FC<AiAssistantProps> = ({ onSendMessage, messages, isLoading }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() === '') return;
    onSendMessage(inputText);
    setInputText('');
  };

  return (
    <>
      {/* Chat panel */}
      {isOpen && (
        <div className="ai-chat-panel">
          <div className="ai-chat-header">
            <span className="ai-chat-title">TalentAI Assistant</span>
            <button className="ai-chat-close" onClick={() => setIsOpen(false)}>x</button>
          </div>
          <div className="ai-chat-messages">
            {messages.slice(-10).map((msg) => (
              <div key={msg.id} className={`ai-chat-msg ${msg.sender}`}>
                <div className="ai-chat-bubble">{msg.text}</div>
              </div>
            ))}
            {isLoading && (
              <div className="ai-chat-msg ai">
                <div className="ai-chat-bubble ai-typing">
                  <span className="dot"></span><span className="dot"></span><span className="dot"></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <form className="ai-chat-input-form" onSubmit={handleSubmit}>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask about candidates..."
              disabled={isLoading}
              className="ai-chat-input"
            />
            <button type="submit" disabled={isLoading} className="ai-chat-send">
              {isLoading ? '...' : 'Send'}
            </button>
          </form>
        </div>
      )}

      {/* Floating toggle button */}
      <button
        className={`ai-fab ${isOpen ? 'ai-fab-active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="TalentAI Assistant"
      >
        <span className="ai-fab-icon">{isOpen ? 'x' : 'AI'}</span>
      </button>
    </>
  );
};

export default AiAssistant;
