import React, { useState, useEffect } from 'react';
import './CandidateCard.css';
import type { Candidate } from '../App';

interface JobOpening {
  id: number;
  job_title: string;
  location: string;
}

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

  const [showAssignDropdown, setShowAssignDropdown] = useState(false);
  const [jobs, setJobs] = useState<JobOpening[]>([]);
  const [assigningId, setAssigningId] = useState<number | null>(null);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);

  // Build candidate object to pass around
  const candidateData: Candidate = {
    initials, name, role, matchScore, matchRank, skillsScore, expScore,
    industryScore, locationScore, statusScore, tags, langs, colorTheme,
    github_url, citation, skill_breakdown, weights,
  };

  const loadJobs = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/job-openings');
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }
    } catch (err) {
      console.error('Failed to load jobs:', err);
    }
  };

  const handleAssignToggle = () => {
    if (!showAssignDropdown && jobs.length === 0) {
      loadJobs();
    }
    setShowAssignDropdown(!showAssignDropdown);
    setAssignSuccess(null);
  };

  const handleAssignToJob = async (jobId: number, jobTitle: string) => {
    setAssigningId(jobId);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/hiring-requests/${jobId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_name: name,
          source: 'talent_pool'
        })
      });
      const data = await res.json();
      if (data.success) {
        setAssignSuccess(`Assigned to ${jobTitle}`);
        setTimeout(() => setShowAssignDropdown(false), 2000);
      } else {
        setAssignSuccess(data.message || 'Already assigned');
      }
    } catch (err) {
      console.error(err);
      setAssignSuccess('Error assigning to job');
    } finally {
      setAssigningId(null);
    }
  };

  return (
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
          <span className="compare-checkbox-box">{compareSelected ? 'Yes' : ''}</span>
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

      {citation && (
        <div className="citation-box">
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
        <div className="assign-job-container">
          <button
            className="btn btn-sm btn-primary"
            onClick={handleAssignToggle}
          >
            Assign to Job
          </button>
          
          {showAssignDropdown && (
            <div className="assign-dropdown">
              <div className="assign-dropdown-header">Select Job Opening</div>
              {jobs.length === 0 ? (
                <div className="assign-dropdown-empty">No open jobs found.</div>
              ) : (
                <div className="assign-dropdown-list">
                  {jobs.map(job => (
                    <button
                      key={job.id}
                      className="assign-dropdown-item"
                      onClick={() => handleAssignToJob(job.id, job.job_title)}
                      disabled={assigningId !== null}
                    >
                      {assigningId === job.id ? 'Assigning...' : job.job_title}
                    </button>
                  ))}
                </div>
              )}
              {assignSuccess && <div className="assign-success-msg">{assignSuccess}</div>}
            </div>
          )}
        </div>

        {onDraftEmail && (
          <button
            className="btn btn-sm btn-secondary draft-email-btn"
            onClick={() => onDraftEmail(name)}
          >
            Draft Email
          </button>
        )}
        {github_url && (
          <a href={github_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm linkedin-btn">
            GitHub
          </a>
        )}
      </div>
    </div>
  );
};

export default CandidateCard;