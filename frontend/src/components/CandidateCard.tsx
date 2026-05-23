import React from 'react';
import './CandidateCard.css';
import type { Candidate } from '../App';

const CandidateCard: React.FC<Candidate> = ({
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
            <span className="label">Experiență:</span>
            <span className="value">{expScore}%</span>
          </div>
          <div className="score-item">
            <span className="label">Locație:</span>
            <span className="value">{locationScore}%</span>
          </div>
        </div>
      </div>

      <div className="card-body">
        <div className="tags-container">
          {tags.map((tag, index) => (
            <span key={index} className="skill-tag">{tag}</span>
          ))}
        </div>
        <div className="languages-info">
          <strong>Limbi străine:</strong> {langs}
        </div>
      </div>
    </div>
  );
};

export default CandidateCard;