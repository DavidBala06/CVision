import React, { useState, useEffect, useRef } from 'react';
import './ChatArea.css';
import CandidateCard from './CandidateCard';
import type { ChatMessage } from '../App';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (query: string) => void;
  isLoading: boolean;
}

const ChatArea: React.FC<ChatAreaProps> = ({ messages, onSendMessage, isLoading }) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() === '') return;
    onSendMessage(inputText);
    setInputText('');
  };

  return (
    <div className="chat-interface">
      <div className="chat-history">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
            <div className="avatar-placeholder">{msg.sender === 'user' ? 'HR' : 'AI'}</div>
            <div className="message-content">
              <div className="message-bubble">{msg.text}</div>
              {msg.candidates && msg.candidates.length > 0 && (
                <div className="inline-candidates-list">
                  {msg.candidates.map((cand, idx) => (
                    <CandidateCard key={idx} {...cand} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper ai">
            <div className="avatar-placeholder">AI</div>
            <div className="message-content">
              <div className="message-bubble typing">
                <span className="dot"></span><span className="dot"></span><span className="dot"></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-form">
          <input 
            type="text" 
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Scrie cerințele jobului (ex: Caut un Python Developer în Cluj...)"
            disabled={isLoading}
            className="chat-input"
          />
          <button type="submit" disabled={isLoading} className="chat-submit-btn">
            {isLoading ? '...' : 'Trimite'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatArea;