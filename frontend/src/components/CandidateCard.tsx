import React, { useState } from 'react';
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
  industryScore,
  locationScore,
  statusScore,
  tags,
  langs,
  colorTheme,
  linkedin_url,
  citation,
  skill_breakdown,
  weights,
  requirements_used,
}) => {
  const [open, setOpen] = useState(false);

  const subScores: Array<[string, number | undefined, number | undefined]> = [
    ['Skills', skillsScore, weights?.skills],
    ['Seniority', expScore, weights?.seniority],
    ['Industry', industryScore, weights?.industry],
    ['Location', locationScore, weights?.location],
    ['Status', statusScore, weights?.status],
  ];

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
          {subScores.map(([label, value, weight]) =>
            value !== undefined ? (
              <div key={label} className="score-item">
                <span className="label">{label} {weight !== undefined && <em>({Math.round(weight * 100)}%)</em>}:</span>
                <span className="value">{value}%</span>
              </div>
            ) : null
          )}
        </div>
      </div>

      <div className="card-body">
        {citation && (
          <div className="citation-box">
            <span className="citation-icon">💡</span>
            <p className="citation-text">{citation}</p>
          </div>
        )}
        <div className="tags-container">
          {tags.map((tag, index) => (
            <span key={index} className="skill-tag">{tag}</span>
          ))}
        </div>
        <div className="languages-info">
          <strong>Languages:</strong> {langs || '—'}
        </div>

        {(skill_breakdown || requirements_used) && (
          <button className="breakdown-toggle" onClick={() => setOpen(!open)}>
            {open ? '▾ Hide score breakdown' : '▸ Show score breakdown'}
          </button>
        )}

        {open && (
          <div className="breakdown-panel">
            {requirements_used && (
              <div className="breakdown-section">
                <strong>Parsed requirements</strong>
                <ul>
                  <li>Skills: {(requirements_used.required_skills || []).join(', ') || '—'}</li>
                  <li>Seniority: {requirements_used.min_seniority || '—'}</li>
                  <li>Industry: {requirements_used.industry || '—'}</li>
                  <li>Location: {requirements_used.location || '—'} {requirements_used.remote_ok ? '(remote OK)' : ''}</li>
                </ul>
              </div>
            )}
            {skill_breakdown && skill_breakdown.length > 0 && (
              <div className="breakdown-section">
                <strong>Skill scoring (exact=1, similar=0.8, no=0)</strong>
                <table className="breakdown-table">
                  <tbody>
                    {skill_breakdown.map((b, i) => (
                      <tr key={i}>
                        <td>{b.skill}</td>
                        <td className={`match-${b.match}`}>{b.match}</td>
                        <td>{b.value.toFixed(1)}</td>
                      </tr>
                    ))}
                    <tr className="breakdown-total">
                      <td><strong>Σ / {skill_breakdown.length}</strong></td>
                      <td>=</td>
                      <td>
                        <strong>
                          {(skill_breakdown.reduce((a, b) => a + b.value, 0) / skill_breakdown.length * 100).toFixed(0)}%
                        </strong>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {linkedin_url && (
        <div className="card-footer">
          <a href={linkedin_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm linkedin-btn">
            🔗 View LinkedIn
          </a>
        </div>
      )}
    </div>
  );
};

export default CandidateCard;
