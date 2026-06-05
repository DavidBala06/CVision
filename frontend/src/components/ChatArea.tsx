import React, { useState, useEffect, useRef } from 'react';
import './ChatArea.css';
import CandidateCard from './CandidateCard';
import ComparePanel from './ComparePanel';
import type { ChatMessage, Candidate } from '../App';

interface ChatAreaProps {
  messages: ChatMessage[];
  onSendMessage: (query: string) => void;
  isLoading: boolean;
  onDraftEmail?: (name: string) => void;
}

const ChatArea: React.FC<ChatAreaProps> = ({ messages, onSendMessage, isLoading, onDraftEmail }) => {
  const [inputText, setInputText] = useState('');
  const [compareList, setCompareList] = useState<Candidate[]>([]);
  const [showCompare, setShowCompare] = useState(false);
  const [lastQuery, setLastQuery] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() === '') return;
    setLastQuery(inputText);
    onSendMessage(inputText);
    setInputText('');
    // Reset compare on new search
    setCompareList([]);
  };

  const handleToggleCompare = (candidate: Candidate) => {
    setCompareList(prev => {
      const exists = prev.find(c => c.name === candidate.name);
      if (exists) return prev.filter(c => c.name !== candidate.name);
      if (prev.length >= 3) return prev; // max 3
      return [...prev, candidate];
    });
  };

  const handleExportCSV = async () => {
    // Collect all shortlisted candidates from the last AI message
    const lastAiWithCandidates = [...messages].reverse().find(m => m.sender === 'ai' && m.candidates?.length);
    if (!lastAiWithCandidates?.candidates) return;

    try {
      const res = await fetch('http://127.0.0.1:8000/api/export-shortlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidates: lastAiWithCandidates.candidates,
          job_description: lastQuery,
        }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shortlist_${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const hasShortlist = messages.some(m => m.sender === 'ai' && m.candidates && m.candidates.length > 0);

  return (
    <div className="chat-interface">
      {/* Toolbar */}
      <div className="chat-toolbar">
        <span className="chat-toolbar-label">
          🔍 AI Shortlisting
        </span>
        <div className="chat-toolbar-actions">
          {compareList.length > 0 && (
            <button
              id="btn-open-compare"
              className="toolbar-btn toolbar-btn-compare"
              onClick={() => setShowCompare(true)}
            >
              ⚖️ Compare ({compareList.length})
            </button>
          )}
          {hasShortlist && (
            <button
              id="btn-export-csv"
              className="toolbar-btn toolbar-btn-export"
              onClick={handleExportCSV}
            >
              ⬇ Export CSV
            </button>
          )}
        </div>
      </div>

      <div className="chat-history">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-wrapper ${msg.sender}`}>
            <div className="message-content">
              <div className="message-bubble">{msg.text}</div>
              {msg.candidates && msg.candidates.length > 0 && (
                <div className="inline-candidates-list">
                  {msg.candidates.map((cand, idx) => (
                    <CandidateCard
                      key={idx}
                      {...cand}
                      onDraftEmail={onDraftEmail}
                      compareSelected={compareList.some(c => c.name === cand.name)}
                      onToggleCompare={handleToggleCompare}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper ai">
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
            placeholder="Describe the job requirements (e.g. Looking for a Python Developer in Cluj...)"
            disabled={isLoading}
            className="chat-input"
          />
          <button type="submit" disabled={isLoading} className="chat-submit-btn">
            {isLoading ? '...' : 'Search'}
          </button>
        </form>
      </div>

      {/* Compare Modal */}
      {showCompare && (
        <ComparePanel
          candidates={compareList}
          onRemove={(name) => setCompareList(prev => prev.filter(c => c.name !== name))}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  );
};

export default ChatArea;