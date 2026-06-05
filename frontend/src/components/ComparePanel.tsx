import React from 'react';
import './ComparePanel.css';
import type { Candidate } from '../App';

interface ComparePanelProps {
  candidates: Candidate[];
  onRemove: (name: string) => void;
  onClose: () => void;
}

const SCORE_FIELDS: { key: keyof Candidate; label: string }[] = [
  { key: 'matchScore', label: 'Overall Match' },
  { key: 'skillsScore', label: 'Skills' },
  { key: 'expScore', label: 'Seniority' },
  { key: 'industryScore', label: 'Industry' },
  { key: 'locationScore', label: 'Location' },
  { key: 'statusScore', label: 'Status' },
];

const ComparePanel: React.FC<ComparePanelProps> = ({ candidates, onRemove, onClose }) => {
  if (candidates.length === 0) return null;

  const getBestIdx = (key: keyof Candidate): number => {
    let best = -1;
    let bestVal = -1;
    candidates.forEach((c, i) => {
      const v = (c[key] as number) ?? 0;
      if (v > bestVal) { bestVal = v; best = i; }
    });
    return best;
  };

  return (
    <div className="compare-panel-overlay" onClick={onClose}>
      <div className="compare-panel" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="compare-header">
          <div className="compare-title">
            <span className="compare-icon">⚖️</span>
            Candidate Comparison
          </div>
          <span className="compare-hint">{candidates.length} candidate{candidates.length !== 1 ? 's' : ''} selected</span>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="compare-body">
          {/* Candidate headers */}
          <div className="compare-grid" style={{ gridTemplateColumns: `160px repeat(${candidates.length}, 1fr)` }}>
            <div className="compare-row-label compare-col-header" />
            {candidates.map((c, i) => (
              <div key={i} className={`compare-col-header theme-${c.colorTheme}`}>
                <div className={`compare-avatar theme-${c.colorTheme}`}>
                  {c.initials}
                </div>
                <div className="compare-cand-name">{c.name}</div>
                <div className="compare-cand-role">{c.role}</div>
                <button className="compare-remove-btn" onClick={() => onRemove(c.name)} title="Remove">✕</button>
              </div>
            ))}

            {/* Score rows */}
            {SCORE_FIELDS.map(({ key, label }) => {
              const bestIdx = getBestIdx(key);
              return (
                <React.Fragment key={key as string}>
                  <div className="compare-row-label">{label}</div>
                  {candidates.map((c, i) => {
                    const val = (c[key] as number) ?? 0;
                    const isBest = i === bestIdx && candidates.length > 1;
                    return (
                      <div key={i} className={`compare-cell ${isBest ? 'best-cell' : ''}`}>
                        <div className="compare-cell-value">{val}%</div>
                        <div className="compare-bar-track">
                          <div
                            className="compare-bar-fill"
                            style={{
                              width: `${val}%`,
                              background: isBest ? '#6366f1' : 'rgba(255,255,255,0.15)',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </React.Fragment>
              );
            })}

            {/* Tags row */}
            <div className="compare-row-label">Top Skills</div>
            {candidates.map((c, i) => (
              <div key={i} className="compare-cell compare-tags-cell">
                {c.tags.slice(0, 4).map((tag, ti) => (
                  <span key={ti} className="compare-tag">{tag}</span>
                ))}
              </div>
            ))}

            {/* GitHub row */}
            <div className="compare-row-label">GitHub</div>
            {candidates.map((c, i) => (
              <div key={i} className="compare-cell">
                {c.github_url
                  ? <a href={c.github_url} target="_blank" rel="noopener noreferrer" className="compare-link">View Profile →</a>
                  : <span className="compare-na">—</span>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComparePanel;
