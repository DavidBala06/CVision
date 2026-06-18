import React, { useState, useEffect } from 'react';
import './CandidateDetailsModal.css';

interface CandidateProfile {
  id: number;
  name: string;
  seniority: string;
  years_of_experience: string;
  current_role: string;
  previous_jobs: string;
  degrees: string;
  location: string;
  languages: string;
  technologies: string;
  project_summary: string;
  linkedin_url: string;
  github_url: string;
  email: string;
  status: string;
  outreach_status: string;
  outreach_date: string;
  last_updated_at: string;
}

interface CandidateDetailsModalProps {
  candidateName: string;
  onClose: () => void;
}

const CandidateDetailsModal: React.FC<CandidateDetailsModalProps> = ({ candidateName, onClose }) => {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchProfile();
  }, [candidateName]);

  const fetchProfile = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/candidates/by-name/${encodeURIComponent(candidateName)}`);
      if (!res.ok) {
        setError('Could not load candidate profile.');
        return;
      }
      const data = await res.json();
      setProfile(data);
    } catch (err) {
      setError('Failed to connect to the server.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      active: 'Active',
      pending_consent: 'Pending Consent',
      stale: 'Stale',
    };
    return map[status] || status;
  };

  const getOutreachLabel = (status: string) => {
    const map: Record<string, string> = {
      not_contacted: 'Not Contacted',
      email_sent: 'Email Sent',
      replied: 'Replied',
      no_reply: 'No Reply',
      interested: 'Interested',
      declined: 'Declined',
    };
    return map[status] || status;
  };

  return (
    <div className="cdm-overlay" onClick={handleOverlayClick}>
      <div className="cdm-panel">
        <button className="cdm-close" onClick={onClose}>x</button>

        {loading && (
          <div className="cdm-loading">
            <span className="spinner"></span> Loading profile...
          </div>
        )}

        {error && (
          <div className="cdm-error">{error}</div>
        )}

        {profile && !loading && (
          <>
            {/* Header */}
            <div className="cdm-header">
              <div className="cdm-avatar">
                {profile.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
              </div>
              <div className="cdm-header-info">
                <h2 className="cdm-name">{profile.name}</h2>
                <div className="cdm-role">{profile.current_role || 'No role specified'}</div>
                <div className="cdm-meta-row">
                  {profile.seniority && <span className="cdm-seniority-pill">{profile.seniority}</span>}
                  {profile.location && <span className="cdm-location">{profile.location}</span>}
                  {profile.years_of_experience && (
                    <span className="cdm-experience">{profile.years_of_experience} years exp.</span>
                  )}
                </div>
              </div>
            </div>

            {/* Contact & Links */}
            <div className="cdm-section cdm-contact-section">
              <h3 className="cdm-section-title">Contact & Links</h3>
              <div className="cdm-contact-grid">
                {profile.email && (
                  <div className="cdm-contact-item">
                    <span className="cdm-contact-label">Email</span>
                    <a href={`mailto:${profile.email}`} className="cdm-contact-value cdm-link">{profile.email}</a>
                  </div>
                )}
                {profile.linkedin_url && (
                  <div className="cdm-contact-item">
                    <span className="cdm-contact-label">LinkedIn</span>
                    <a href={profile.linkedin_url} target="_blank" rel="noopener noreferrer" className="cdm-contact-value cdm-link">
                      {profile.linkedin_url.replace(/^https?:\/\/(www\.)?linkedin\.com\/in\//, '').replace(/\/$/, '')}
                    </a>
                  </div>
                )}
                {profile.github_url && (
                  <div className="cdm-contact-item">
                    <span className="cdm-contact-label">GitHub</span>
                    <a href={profile.github_url} target="_blank" rel="noopener noreferrer" className="cdm-contact-value cdm-link">
                      {profile.github_url.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\/$/, '')}
                    </a>
                  </div>
                )}
                {!profile.email && !profile.linkedin_url && !profile.github_url && (
                  <div className="cdm-empty-field">No contact information available.</div>
                )}
              </div>
            </div>

            {/* Summary / Bio */}
            {profile.project_summary && (
              <div className="cdm-section">
                <h3 className="cdm-section-title">Summary</h3>
                <p className="cdm-summary-text">{profile.project_summary}</p>
              </div>
            )}

            {/* Technologies */}
            {profile.technologies && (
              <div className="cdm-section">
                <h3 className="cdm-section-title">Technologies</h3>
                <div className="cdm-tech-tags">
                  {profile.technologies.split(',').map((tech, i) => (
                    <span key={i} className="cdm-tech-tag">{tech.trim()}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Experience / Previous Jobs */}
            {profile.previous_jobs && (
              <div className="cdm-section">
                <h3 className="cdm-section-title">Experience</h3>
                <div className="cdm-text-block">{profile.previous_jobs}</div>
              </div>
            )}

            {/* Education */}
            {profile.degrees && (
              <div className="cdm-section">
                <h3 className="cdm-section-title">Education</h3>
                <div className="cdm-text-block">{profile.degrees}</div>
              </div>
            )}

            {/* Languages */}
            {profile.languages && (
              <div className="cdm-section">
                <h3 className="cdm-section-title">Languages</h3>
                <div className="cdm-text-block">{profile.languages}</div>
              </div>
            )}

            {/* System Status */}
            <div className="cdm-section cdm-status-section">
              <h3 className="cdm-section-title">Status</h3>
              <div className="cdm-status-grid">
                <div className="cdm-status-item">
                  <span className="cdm-status-label">Pool Status</span>
                  <span className={`cdm-status-value status-${profile.status}`}>
                    {getStatusLabel(profile.status)}
                  </span>
                </div>
                <div className="cdm-status-item">
                  <span className="cdm-status-label">Outreach</span>
                  <span className="cdm-status-value">
                    {getOutreachLabel(profile.outreach_status)}
                  </span>
                </div>
                {profile.last_updated_at && (
                  <div className="cdm-status-item">
                    <span className="cdm-status-label">Last Updated</span>
                    <span className="cdm-status-value">{profile.last_updated_at}</span>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CandidateDetailsModal;
