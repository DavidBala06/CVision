import React, { useState, useEffect } from 'react';
import './HiringRequests.css';

interface HiringRequest {
  id: number;
  job_title: string;
  description: string;
  location: string;
  hiring_manager: string;
  open_date: string;
  end_date: string;
  status: string;
  total_applicants: number;
  in_progress: number;
}

interface HiringRequestsProps {
  onOpenApplications: (id: number) => void;
}

const HiringRequests: React.FC<HiringRequestsProps> = ({ onOpenApplications }) => {
  const [requests, setRequests] = useState<HiringRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/hiring-requests');
      if (res.ok) {
        const data = await res.json();
        setRequests(data);
      }
    } catch (err) {
      console.error('Failed to fetch hiring requests:', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = requests.filter(r => {
    if (filterStatus === 'all') return true;
    return r.status === filterStatus;
  });

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      open: 'badge-active',
      draft: 'badge-pending',
      closed: 'badge-stale',
      on_hold: 'badge-no-reply',
    };
    return <span className={`badge ${map[status] || 'badge-pending'}`}>{status.replace('_', ' ')}</span>;
  };

  const statuses = ['all', ...new Set(requests.map(r => r.status).filter(Boolean))];

  if (loading) {
    return (
      <div className="hiring-requests">
        <div className="loading-spinner"><span className="spinner"></span> Loading hiring requests...</div>
      </div>
    );
  }

  return (
    <div className="hiring-requests">
      <div className="section-header">
        <div>
          <div className="section-title">Hiring Requests</div>
          <div className="section-subtitle">{requests.length} job openings in the pipeline</div>
        </div>
      </div>

      <div className="hr-filters">
        <select className="form-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          {statuses.map(s => <option key={s} value={s}>{s === 'all' ? 'All Status' : s.replace('_', ' ')}</option>)}
        </select>
        <span className="filter-count">{filtered.length} results</span>
      </div>

      <div className="table-container">
        <table className="talent-table">
          <thead>
            <tr>
              <th>Job Title</th>
              <th>Total Applicants</th>
              <th>In Progress</th>
              <th>Location</th>
              <th>Hiring Manager</th>
              <th>Open Date</th>
              <th>End Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr
                key={r.id}
                className="table-row clickable-row"
                onClick={() => onOpenApplications(r.id)}
              >
                <td className="cell-name">
                  <div className="job-title-text">{r.job_title}</div>
                </td>
                <td>
                  <span className="count-badge">{r.total_applicants}</span>
                </td>
                <td>
                  <span className="count-badge count-progress">{r.in_progress}</span>
                </td>
                <td>{r.location || '--'}</td>
                <td>{r.hiring_manager || '--'}</td>
                <td>{r.open_date || '--'}</td>
                <td>{r.end_date || '--'}</td>
                <td>{getStatusBadge(r.status)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-text">No hiring requests match your filters</div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HiringRequests;
