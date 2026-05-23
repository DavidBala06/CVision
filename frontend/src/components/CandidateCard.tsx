import React from 'react';
import './CandidateCard.css';
import { ExternalLink } from 'lucide-react';

interface CandidateCardProps {
  initials: string;
  name: string;
  role: string;
  matchScore: number;
  matchRank: string;
  skillsScore: number;
  expScore: number;
  locationScore: number;
  tags: string[];
  langs: string;
  colorTheme?: 'purple' | 'green' | 'blue';
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
  colorTheme = 'purple'
}) => {
  return (
    <div className={`candidate-card theme-${colorTheme}`}>
      <div className="card-header">
        <div className="card-avatar">{initials}</div>
        <div className="match-badge">{matchRank}</div>
      </div>
      <div className="card-info">
        <h3>{name}</h3>
        <p>{role}</p>
      </div>
      <div className="card-stats">
        <div className="score-circle">
          <svg viewBox="0 0 36 36" className="circular-chart">
            <path className="circle-bg"
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path className="circle"
              strokeDasharray={`${matchScore}, 100`}
              d="M18 2.0845
                a 15.9155 15.9155 0 0 1 0 31.831
                a 15.9155 15.9155 0 0 1 0 -31.831"
            />
          </svg>
          <div className="score-text">
            <span className="score-num">{matchScore}</span>
            <span className="score-label">score</span>
          </div>
        </div>
        <div className="bar-charts">
          <div className="bar-row">
            <span>Skills</span>
            <div className="bar-container"><div className="bar-fill" style={{ width: `${skillsScore}%` }}></div></div>
            <span className="bar-value">{skillsScore}</span>
          </div>
          <div className="bar-row">
            <span>Exp.</span>
            <div className="bar-container"><div className="bar-fill" style={{ width: `${expScore}%` }}></div></div>
            <span className="bar-value">{expScore}</span>
          </div>
          <div className="bar-row">
            <span>Location</span>
            <div className="bar-container"><div className="bar-fill" style={{ width: `${locationScore}%` }}></div></div>
            <span className="bar-value">{locationScore}</span>
          </div>
        </div>
      </div>
      <div className="card-tags">
        <div className="skill-tags">
          {tags.map(tag => <span key={tag} className="tag">{tag}</span>)}
        </div>
        <div className="lang-tags">
          <span className="tag lang">{langs}</span>
        </div>
      </div>
      <div className="card-actions">
        <button className="action-btn">Draft email <ExternalLink size={14} /></button>
        <button className="action-btn outline">View profile</button>
      </div>
    </div>
  );
};

export default CandidateCard;
