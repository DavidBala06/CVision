import React from 'react';
import './CandidateCard.css';
import type { Candidate } from '../App';

interface CandidateCardProps extends Candidate {
  onDraftEmail?: (name: string) => void;
}

const CandidateCard: React.FC<CandidateCardProps> = ({
  initials,
  name,
  role,
  matchScore,
  matchRank,
  skillsScore,
  expScore,
  locationScore,
  tags,
  langs,
  colorTheme,
  linkedin_url,
  citation,
  onDraftEmail,
}) => {
  return (
    <div className={`candidate-card theme-${colorTheme || 'blue'}`}>
      <div className="card-header">
        <div className="avatar-circle">{initials}</div>
        <div className="candidate-info">
          <h3>{name}</h3>
          <p className="role-text">{role}</p>
        </div>
        <div className="rank-badge">{matchRank}</div>
      </div>

      <div className="scores-row">
        <div className="main-score">
          <span className="score-value">{matchScore}%</span>
          <span className="score-label">Match</span>
        </div>
        <div className="sub-scores">
          <div className="score-item">
            <span className="label">Skills:</span>
            <span className="value">{skillsScore}%</span>
          </div>
          <div className="score-item">
            <span className="label">Experience:</span>
            <span className="value">{expScore}%</span>
          </div>
          <div className="score-item">
            <span className="label">Location:</span>
            <span className="value">{locationScore}%</span>
          </div>
        </div>
      </div>

      <div className="card-body">
        {citation && (
          <div className="citation-box">
            <span className="citation-icon">💡</span>
            <p className="citation-text">"{citation}"</p>
          </div>
        )}
        <div className="tags-container">
          {tags.map((tag, index) => (
            <span key={index} className="skill-tag">{tag}</span>
          ))}
        </div>
        <div className="languages-info">
          <strong>Languages:</strong> {langs}
        </div>
      </div>
      
      <div className="card-footer">
        {onDraftEmail && (
          <button
            className="btn btn-sm btn-primary draft-email-btn"
            onClick={() => onDraftEmail(name)}
          >
            ✉️ Draft Email
          </button>
        )}
        {linkedin_url && (
          <a href={linkedin_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm linkedin-btn">
            🔗 View LinkedIn
          </a>
        )}
      </div>
    </div>
  );
};

export default CandidateCard;