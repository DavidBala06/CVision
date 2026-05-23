import React, { useState } from 'react';
import { Paperclip, Link as LinkIcon, FileText, Send, Sparkles } from 'lucide-react';
import CandidateCard from './CandidateCard';
import './ChatArea.css';

const ChatArea: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [candidates, setCandidates] = useState<any[]>([]);

  const handleSearch = async () => {
    if (!inputValue.trim()) return;
    
    setHasSearched(true);
    setIsLoading(true);
    setSearchQuery(inputValue);
    
    try {
      const response = await fetch('http://localhost:8000/api/match', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: inputValue })
      });
      
      if (response.ok) {
        const data = await response.json();
        setCandidates(data);
      } else {
        console.error('Failed to fetch candidates');
        setCandidates([]);
      }
    } catch (error) {
      console.error('Error fetching candidates:', error);
      setCandidates([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <main className="chat-area">
      <header className="chat-header">
        <div className="header-titles">
          <h2>CV Extraction & Candidate Matching</h2>
          <div className="header-subtitle">module: extract · shortlist · draft</div>
        </div>
        <div className="header-badges">
          <div className="badge active-badge"><span className="dot"></span> Agent active</div>
          <div className="badge outline-badge">Human-in-loop</div>
        </div>
      </header>

      <div className="results-area">
        {!hasSearched ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Sparkles size={32} />
            </div>
            <h3>Ready to find your next great hire</h3>
            <p>Describe a role, paste a job description, or drop a CV to instantly shortlist top matches from your talent pool.</p>
          </div>
        ) : isLoading ? (
          <div className="empty-state">
            <div className="empty-state-icon" style={{ animation: 'pulse 1.5s infinite' }}>
              <Sparkles size={32} />
            </div>
            <h3>Analyzing talent pool...</h3>
            <p>Running matching algorithm against your query.</p>
          </div>
        ) : (
          <>
            <div className="results-header">
              <h3>Matching run against: <span className="highlight-role">{searchQuery}</span></h3>
              <p>{candidates.length} candidates found in the database.</p>
            </div>
            
            <div className="candidate-cards-container">
              {candidates.length > 0 ? (
                candidates.map((c, i) => (
                  <CandidateCard 
                    key={i}
                    initials={c.initials || "NA"} 
                    name={c.name || "Unknown"} 
                    role={c.role || "Candidate"}
                    matchScore={c.matchScore || 0} 
                    matchRank={c.matchRank || ""}
                    skillsScore={c.skillsScore || 0} 
                    expScore={c.expScore || 0} 
                    locationScore={c.locationScore || 0}
                    tags={c.tags || []} 
                    langs={c.langs || ""} 
                    colorTheme={c.colorTheme || "purple"}
                  />
                ))
              ) : (
                 <div className="empty-state" style={{ padding: '0' }}>
                   <p>No suitable candidates found in the current pool for this query.</p>
                 </div>
              )}
            </div>
          </>
        )}
      </div>

      <div className="chat-input-area">
        <div className="chat-input-wrapper">
          <textarea 
            placeholder="Paste a CV, describe a role, or ask to shortlist candidates..." 
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
          ></textarea>
          <div className="input-actions">
            <button className="icon-btn"><Paperclip size={18} /></button>
            <button className="icon-btn"><LinkIcon size={18} /></button>
            <button className="icon-btn"><FileText size={18} /></button>
            <div className="spacer"></div>
            <span className="char-count">{inputValue.length}</span>
            <button className="send-btn" onClick={handleSearch}><Send size={16} /></button>
          </div>
        </div>
        <div className="input-footer">Agent has no external send permissions · all outputs require human approval</div>
      </div>
    </main>
  );
};

export default ChatArea;
