import React, { useState, useEffect } from 'react';
import './ApplicationsPool.css';

interface ApplicationEntry {
  id: number;
  hiring_request_id: number;
  candidate_id: number | null;
  candidate_name: string;
  source: string;
  applied_date: string;
  step: string;
  category: string;
  notes: string;
  current_role?: string;
  years_of_experience?: string;
  degrees?: string;
  location?: string;
}

interface HiringRequestSummary {
  id: number;
  job_title: string;
  location: string;
  status: string;
  total_applicants: number;
  in_progress: number;
}

interface ApplicationsPoolProps {
  hiringRequestId: number | null;
  onBack: () => void;
  onEngage?: (candidateName: string) => void;
}

const STEP_ORDER = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected'];

const ApplicationsPool: React.FC<ApplicationsPoolProps> = ({ hiringRequestId, onBack, onEngage }) => {
  const [hiringRequest, setHiringRequest] = useState<HiringRequestSummary | null>(null);
  const [applicants, setApplicants] = useState<ApplicationEntry[]>([]);
  const [leads, setLeads] = useState<ApplicationEntry[]>([]);
  const [activeCategory, setActiveCategory] = useState<'applicants' | 'leads'>('applicants');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (hiringRequestId) {
      fetchApplications(hiringRequestId);
    }
  }, [hiringRequestId]);

  const fetchApplications = async (id: number) => {
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/hiring-requests/${id}/applications`);
      if (res.ok) {
        const data = await res.json();
        setHiringRequest(data.hiring_request);
        setApplicants(data.applicants || []);
        setLeads(data.leads || []);
      }
    } catch (err) {
      console.error('Failed to fetch applications:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStepBadge = (step: string) => {
    const map: Record<string, string> = {
      applied: 'step-applied',
      screening: 'step-screening',
      interview: 'step-interview',
      offer: 'step-offer',
      hired: 'step-hired',
      rejected: 'step-rejected',
    };
    return <span className={`step-badge ${map[step] || 'step-applied'}`}>{step}</span>;
  };

  const getSourceBadge = (source: string) => {
    const labels: Record<string, string> = {
      referral: 'Referral',
      internal: 'Internal',
      linnify: 'Linnify',
      linkedin: 'LinkedIn',
      github: 'GitHub',
      talent_pool: 'Talent Pool',
      cv_upload: 'CV Upload',
    };
    return <span className="source-badge">{labels[source] || source}</span>;
  };

  const currentList = activeCategory === 'applicants' ? applicants : leads;

  if (loading) {
    return (
      <div className="applications-pool">
        <div className="loading-spinner"><span className="spinner"></span> Loading applications...</div>
      </div>
    );
  }

  if (!hiringRequest) {
    return (
      <div className="applications-pool">
        <div className="empty-state">
          <div className="empty-state-text">No hiring request selected.</div>
          <button className="btn btn-secondary" onClick={onBack}>Back to Hiring Requests</button>
        </div>
      </div>
    );
  }

  return (
    <div className="applications-pool">
      <div className="section-header">
        <div className="ap-header-left">
          <button className="btn btn-secondary btn-sm ap-back-btn" onClick={onBack}>
            Back
          </button>
          <div>
            <div className="section-title">{hiringRequest.job_title}</div>
            <div className="section-subtitle">
              {hiringRequest.location} &middot; {hiringRequest.total_applicants} total candidates
            </div>
          </div>
        </div>
      </div>

      <div className="ap-category-tabs">
        <button
          className={`ap-cat-btn ${activeCategory === 'applicants' ? 'active' : ''}`}
          onClick={() => setActiveCategory('applicants')}
        >
          Applicants <span className="ap-cat-count">{applicants.length}</span>
        </button>
        <button
          className={`ap-cat-btn ${activeCategory === 'leads' ? 'active' : ''}`}
          onClick={() => setActiveCategory('leads')}
        >
          Leads <span className="ap-cat-count">{leads.length}</span>
        </button>
      </div>

      <div className="table-container">
        <table className="talent-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Source</th>
              <th>Applied</th>
              <th>Step</th>
              <th>Current / Last Job</th>
              <th>Experience</th>
              <th>Education</th>
              <th>Location</th>
              {onEngage && <th>Engage</th>}
            </tr>
          </thead>
          <tbody>
            {currentList.map((app) => (
              <tr key={app.id} className="table-row">
                <td className="cell-name">
                  <div className="name-text">{app.candidate_name}</div>
                </td>
                <td>{getSourceBadge(app.source)}</td>
                <td>{app.applied_date || '--'}</td>
                <td>{getStepBadge(app.step)}</td>
                <td>{app.current_role || '--'}</td>
                <td>{app.years_of_experience ? `${app.years_of_experience}y` : '--'}</td>
                <td className="cell-education">{app.degrees || '--'}</td>
                <td>{app.location || '--'}</td>
                {onEngage && (
                  <td>
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => onEngage(app.candidate_name)}
                    >
                      Engage
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {currentList.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-text">
              No {activeCategory} for this job yet.
              {activeCategory === 'leads' && ' Use Find & Match to assign candidates.'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ApplicationsPool;
