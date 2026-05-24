import React, { useState, useEffect } from 'react';
import './Outreach.css';
import type { PoolCandidate } from '../App';

interface OutreachProps {
  candidates: PoolCandidate[];
  preselectedCandidate?: string;
}

interface OutreachCandidate {
  name: string;
  current_role: string;
  email: string;
  outreach_status: string;
  outreach_date: string;
  needs_followup: boolean;
}

const Outreach: React.FC<OutreachProps> = ({ candidates, preselectedCandidate }) => {
  const [selectedCandidate, setSelectedCandidate] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [emailDraft, setEmailDraft] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [outreachData, setOutreachData] = useState<{ candidates: OutreachCandidate[]; summary: Record<string, number> }>({ candidates: [], summary: {} });
  const [activeSubTab, setActiveSubTab] = useState<'compose' | 'monitor'>('compose');

  useEffect(() => {
    fetchOutreachStatus();
  }, []);

  // Auto-select candidate when navigated from shortlist "Draft Email"
  useEffect(() => {
    if (preselectedCandidate) {
      setSelectedCandidate(preselectedCandidate);
      setActiveSubTab('compose');
    }
  }, [preselectedCandidate]);

  const fetchOutreachStatus = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/outreach-status');
      if (res.ok) {
        const data = await res.json();
        setOutreachData(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerateEmail = async () => {
    if (!selectedCandidate || !jobDescription.trim()) return;
    setIsGenerating(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/draft-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: selectedCandidate, job_description: jobDescription }),
      });
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setEmailDraft(data.email_draft);
    } catch (err) {
      setEmailDraft(`Error: ${err}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGenerateFollowup = async (name: string) => {
    setIsGenerating(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/draft-followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: name }),
      });
      if (!res.ok) throw new Error(`Error: ${res.status}`);
      const data = await res.json();
      setSelectedCandidate(name);
      setEmailDraft(data.followup_draft);
      setActiveSubTab('compose');
    } catch (err) {
      console.error(err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleMarkAsSent = async () => {
    if (!selectedCandidate) return;
    try {
      await fetch('http://127.0.0.1:8000/api/outreach-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: selectedCandidate, status: 'email_sent' }),
      });
      fetchOutreachStatus();
      setEmailDraft('');
    } catch (err) { console.error(err); }
  };

  const handleUpdateStatus = async (name: string, status: string) => {
    try {
      await fetch('http://127.0.0.1:8000/api/outreach-status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_name: name, status }),
      });
      fetchOutreachStatus();
    } catch (err) { console.error(err); }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(emailDraft);
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      email_sent: 'badge-sent', replied: 'badge-replied', no_reply: 'badge-no-reply',
      interested: 'badge-active', declined: 'badge-stale',
    };
    return <span className={`badge ${map[status] || 'badge-pending'}`}>{status.replace('_', ' ')}</span>;
  };

  return (
    <div className="outreach">
      <div className="section-header">
        <div>
          <div className="section-title">Outreach & Communication</div>
          <div className="section-subtitle">Module 3: Email drafts + progress monitoring</div>
        </div>
        <div className="outreach-tabs">
          <button className={`btn btn-sm ${activeSubTab === 'compose' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveSubTab('compose')}>
            ✍️ Compose
          </button>
          <button className={`btn btn-sm ${activeSubTab === 'monitor' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setActiveSubTab('monitor')}>
            Monitor
          </button>
        </div>
      </div>

      <div className="outreach-content">
        {activeSubTab === 'compose' && (
          <div className="compose-view">
            <div className="compose-form">
              <div className="form-group">
                <label className="form-label">Select Candidate</label>
                <select className="form-select" value={selectedCandidate} onChange={e => setSelectedCandidate(e.target.value)}>
                  <option value="">Choose a candidate...</option>
                  {candidates.map((c, i) => (
                    <option key={i} value={c.name}>{c.name} — {c.current_role || c.seniority}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Job Description / Context</label>
                <textarea
                  className="form-textarea"
                  placeholder="Describe the job opportunity (role, requirements, company info)..."
                  value={jobDescription}
                  onChange={e => setJobDescription(e.target.value)}
                  rows={5}
                />
              </div>

              <button className="btn btn-primary" onClick={handleGenerateEmail} disabled={isGenerating || !selectedCandidate || !jobDescription.trim()}>
                {isGenerating ? <><span className="spinner"></span> Generating...</> : 'Generate Email Draft'}
              </button>
            </div>

            {emailDraft && (
              <div className="email-preview">
                <div className="preview-header">
                  <span className="preview-title">📧 Email Draft for {selectedCandidate}</span>
                  <div className="preview-actions">
                    <button className="btn btn-sm btn-secondary" onClick={copyToClipboard}>📋 Copy</button>
                    <button className="btn btn-sm btn-success" onClick={handleMarkAsSent}>Mark as Sent</button>
                  </div>
                </div>
                <textarea
                  className="form-textarea email-textarea"
                  value={emailDraft}
                  onChange={e => setEmailDraft(e.target.value)}
                  rows={12}
                />
              </div>
            )}
          </div>
        )}

        {activeSubTab === 'monitor' && (
          <div className="monitor-view">
            <div className="monitor-summary">
              {Object.entries(outreachData.summary).map(([status, count]) => (
                <div key={status} className="summary-card">
                  <div className="summary-value">{count}</div>
                  <div className="summary-label">{status.replace('_', ' ')}</div>
                </div>
              ))}
            </div>

            <div className="monitor-table">
              <table className="talent-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Sent Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {outreachData.candidates.map((c, i) => (
                    <tr key={i} className="table-row">
                      <td className="name-text">{c.name}</td>
                      <td>{c.current_role || '—'}</td>
                      <td className="name-email">{c.email || '—'}</td>
                      <td>{getStatusBadge(c.outreach_status)}</td>
                      <td>{c.outreach_date || '—'}</td>
                      <td className="action-cell">
                        {c.needs_followup && (
                          <button className="btn btn-sm btn-secondary" onClick={() => handleGenerateFollowup(c.name)}>
                            📩 Follow-up
                          </button>
                        )}
                        {c.outreach_status === 'email_sent' && (
                          <>
                            <button className="btn btn-sm btn-success" onClick={() => handleUpdateStatus(c.name, 'replied')}>Replied</button>
                            <button className="btn btn-sm btn-danger" onClick={() => handleUpdateStatus(c.name, 'no_reply')}>No Reply</button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                  {outreachData.candidates.length === 0 && (
                    <tr><td colSpan={6}>
                      <div className="empty-state">
                        <div className="empty-state-icon">📭</div>
                        <div className="empty-state-text">No outreach activity yet. Compose your first email!</div>
                      </div>
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Outreach;
