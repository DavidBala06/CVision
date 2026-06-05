import React, { useState } from 'react';
import './CandidateCard.css';
import type { Candidate } from '../App';
import ScoreModal from './ScoreModal';

interface CandidateCardProps extends Candidate {
  onDraftEmail?: (name: string) => void;
  compareSelected?: boolean;
  onToggleCompare?: (candidate: Candidate) => void;
}

const CandidateCard: React.FC<CandidateCardProps> = (props) => {
  const {
    initials, name, role, matchScore, matchRank, skillsScore, expScore,
    industryScore, locationScore, statusScore, tags, langs, colorTheme,
    github_url, citation, onDraftEmail, skill_breakdown, weights,
    compareSelected, onToggleCompare,
  } = props;

  const [showModal, setShowModal] = useState(false);

  // Build candidate object to pass around
  const candidateData: Candidate = {
    initials, name, role, matchScore, matchRank, skillsScore, expScore,
    industryScore, locationScore, statusScore, tags, langs, colorTheme,
    github_url, citation, skill_breakdown, weights,
  };

  return (
    <>
      <div className={`candidate-card theme-${colorTheme || 'blue'} ${compareSelected ? 'card-selected' : ''}`}>
        {/* Compare checkbox */}
        {onToggleCompare && (
          <label className="compare-checkbox-label" title="Add to comparison">
            <input
              type="checkbox"
              className="compare-checkbox"
              checked={compareSelected ?? false}
              onChange={() => onToggleCompare(candidateData)}
            />
            <span className="compare-checkbox-box">{compareSelected ? '✓' : ''}</span>
            Compare
          </label>
        )}

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
              <span className="label">Seniority:</span>
              <span className="value">{expScore}%</span>
            </div>
            {industryScore !== undefined && (
              <div className="score-item">
                <span className="label">Industry:</span>
                <span className="value">{industryScore}%</span>
              </div>
            )}
            <div className="score-item">
              <span className="label">Location:</span>
              <span className="value">{locationScore}%</span>
            </div>
            {statusScore !== undefined && (
              <div className="score-item">
                <span className="label">Status:</span>
                <span className="value">{statusScore}%</span>
              </div>
            )}
          </div>
        </div>

        {/* Why This Score button */}
        <button
          id={`why-score-${name.replace(/\s+/g, '-').toLowerCase()}`}
          className="why-score-btn"
          onClick={() => setShowModal(true)}
        >
          🔍 Why this score?
        </button>

        {citation && (
          <div className="citation-box">
            <span className="citation-icon">💬</span>
            <span className="citation-text">{citation}</span>
          </div>
        )}

        <div className="card-body">
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
              Draft Email
            </button>
          )}
          {github_url && (
            <a href={github_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm linkedin-btn">
              View GitHub
            </a>
          )}
        </div>
      </div>

      {showModal && (
        <ScoreModal candidate={candidateData} onClose={() => setShowModal(false)} />
      )}
    </>
  );
};

export default CandidateCard;