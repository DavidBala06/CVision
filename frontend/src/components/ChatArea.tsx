import React, { useState } from 'react';
import { Paperclip, Link as LinkIcon, FileText, Send, Sparkles } from 'lucide-react';
import CandidateCard from './CandidateCard';
import './ChatArea.css';

const ChatArea: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = () => {
    if (inputValue.trim()) {
      setHasSearched(true);
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
        ) : (
          <>
            <div className="results-header">
              <h3>Matching run against: <span className="highlight-role">Product Manager</span></h3>
              <p>Top 3 candidates found in the database.</p>
            </div>
            
            <div className="candidate-cards-container">
                <CandidateCard 
                  initials="AM" name="Ana Marinescu" role="Senior PM · Bucharest"
                  matchScore={91} matchRank="#1 match"
                  skillsScore={95} expScore={88} locationScore={100}
                  tags={['Agile', 'SQL', 'Figma']} langs="EN · RO · IT" colorTheme="purple"
                />
                <CandidateCard 
                  initials="RT" name="Radu Tănase" role="Lead BA · Cluj-Napoca"
                  matchScore={80} matchRank="#2 match"
                  skillsScore={82} expScore={91} locationScore={75}
                  tags={['Jira', 'Python', 'GovTech']} langs="EN · RO" colorTheme="green"
                />
                <CandidateCard 
                  initials="IC" name="Irina Constantin" role="Product Manager · Remote"
                  matchScore={72} matchRank="#3 match"
                  skillsScore={70} expScore={74} locationScore={80}
                  tags={['Roadmaps', 'Stakeholders']} langs="EN · RO" colorTheme="blue"
                />
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
