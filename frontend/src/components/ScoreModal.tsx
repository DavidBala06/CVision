import React from 'react';
import './ScoreModal.css';
import type { Candidate } from '../App';

interface ScoreModalProps {
  candidate: Candidate;
  onClose: () => void;
}

const ScoreModal: React.FC<ScoreModalProps> = ({ candidate, onClose }) => {
  const {
    name, role, matchScore, matchRank, colorTheme,
    skillsScore, expScore, industryScore = 0, locationScore, statusScore = 0,
    skill_breakdown = [], weights = {}, citation,
  } = candidate;

  const bars = [
    { label: 'Skills', score: skillsScore, weight: weights.skills ?? 0.45, color: '#6366f1' },
    { label: 'Seniority', score: expScore, weight: weights.seniority ?? 0.20, color: '#8b5cf6' },
    { label: 'Industry', score: industryScore, weight: weights.industry ?? 0.15, color: '#06b6d4' },
    { label: 'Location', score: locationScore, weight: weights.location ?? 0.15, color: '#10b981' },
    { label: 'Status', score: statusScore, weight: weights.status ?? 0.05, color: '#f59e0b' },
  ];

  const matchTypeColor: Record<string, string> = {
    exact: '#4ade80',
    similar: '#fbbf24',
    none: '#f87171',
  };

  const matchTypeLabel: Record<string, string> = {
    exact: '✓ Exact',
    similar: '≈ Similar',
    none: '✗ Missing',
  };

  return (
    <div className="score-modal-overlay" onClick={onClose}>
      <div className={`score-modal theme-${colorTheme}`} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <div className={`modal-avatar theme-${colorTheme}`}>
              {name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="modal-name">{name}</div>
              <div className="modal-role">{role}</div>
            </div>
          </div>
          <div className="modal-score-badge">
            <span className="modal-score-num">{matchScore}%</span>
            <span className="modal-score-rank">{matchRank}</span>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Score Bars */}
          <div className="modal-section">
            <div className="modal-section-title">Match Score Breakdown</div>
            <div className="score-bars">
              {bars.map(bar => (
                <div key={bar.label} className="score-bar-row">
                  <div className="score-bar-meta">
                    <span className="score-bar-label">{bar.label}</span>
                    <span className="score-bar-weight">×{(bar.weight * 100).toFixed(0)}% weight</span>
                    <span className="score-bar-value">{bar.score}%</span>
                  </div>
                  <div className="score-bar-track">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${bar.score}%`,
                        background: bar.color,
                        boxShadow: `0 0 8px ${bar.color}55`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Formula */}
          <div className="modal-section formula-section">
            <div className="modal-section-title">Formula</div>
            <code className="formula-code">
              score = 0.45×skills + 0.20×seniority + 0.15×industry + 0.15×location + 0.05×status
            </code>
          </div>

          {/* Skill-by-skill breakdown */}
          {skill_breakdown.length > 0 && (
            <div className="modal-section">
              <div className="modal-section-title">Skill Match Details</div>
              <div className="skill-breakdown-table">
                <div className="sbt-header">
                  <span>Required Skill</span>
                  <span>Match Type</span>
                  <span>Score</span>
                </div>
                {skill_breakdown.map((item, idx) => (
                  <div key={idx} className={`sbt-row match-${item.match}`}>
                    <span className="sbt-skill">{item.skill}</span>
                    <span className="sbt-match" style={{ color: matchTypeColor[item.match] }}>
                      {matchTypeLabel[item.match] ?? item.match}
                    </span>
                    <span className="sbt-value">{Math.round(item.value * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Citation */}
          {citation && (
            <div className="modal-section">
              <div className="modal-section-title">Why This Candidate</div>
              <div className="modal-citation">{citation}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScoreModal;
