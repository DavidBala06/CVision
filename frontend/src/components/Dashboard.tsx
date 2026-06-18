import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import type { PoolCandidate } from '../App';
import HealthBanner from './HealthBanner';

interface HiringRequestSummary {
  id: number;
  job_title: string;
  location: string;
  status: string;
  total_applicants: number;
  in_progress: number;
}

interface DashboardProps {
  candidates: PoolCandidate[];
  onRefresh: () => void;
  onNavigate?: (tab: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ candidates, onRefresh, onNavigate }) => {
  const [dashboardView, setDashboardView] = useState<'overview' | 'database'>('overview');

  // --- Overview state ---
  const [activeJobs, setActiveJobs] = useState<HiringRequestSummary[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [pipelineStats, setPipelineStats] = useState({
    applied: 0, screening: 0, interview: 0, offer: 0,
  });

  // --- Database state ---
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSeniority, setFilterSeniority] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [refreshing, setRefreshing] = useState(false);
  const [staleCount, setStaleCount] = useState<number | null>(null);

  useEffect(() => {
    fetchActiveJobs();
    fetchPipelineStats();
  }, []);

  const fetchActiveJobs = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/hiring-requests');
      if (res.ok) {
        const data = await res.json();
        const openJobs = data.filter((j: HiringRequestSummary) => j.status === 'open').slice(0, 5);
        setActiveJobs(openJobs);
      }
    } catch (err) {
      console.error('Failed to fetch active jobs:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const fetchPipelineStats = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/hiring-requests');
      if (res.ok) {
        const jobs = await res.json();
        let stats = { applied: 0, screening: 0, interview: 0, offer: 0 };
        for (const job of jobs) {
          const appRes = await fetch(`http://127.0.0.1:8000/api/hiring-requests/${job.id}/applications`);
          if (appRes.ok) {
            const appData = await appRes.json();
            const allApps = [...(appData.applicants || []), ...(appData.leads || [])];
            allApps.forEach(a => {
              if (a.step in stats) {
                stats[a.step as keyof typeof stats]++;
              }
            });
          }
        }
        setPipelineStats(stats);
      }
    } catch (err) {
      console.error('Failed to fetch pipeline stats:', err);
    }
  };

  // --- Database filters ---
  const filtered = candidates.filter(c => {
    const matchesSearch = searchTerm === '' ||
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.technologies.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.location.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSeniority = filterSeniority === 'all' || c.seniority === filterSeniority;
    const matchesStatus = filterStatus === 'all' || c.status === filterStatus;
    return matchesSearch && matchesSeniority && matchesStatus;
  });

  const handleCheckStale = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/refresh/stale');
      const data = await res.json();
      setStaleCount(data.count);
    } catch { setStaleCount(0); }
  };

  const handleRefreshAll = async () => {
    setRefreshing(true);
    try {
      const staleRes = await fetch('http://127.0.0.1:8000/api/refresh/stale');
      const staleData = await staleRes.json();
      const names = staleData.stale_candidates.map((c: any) => c.name);
      if (names.length > 0) {
        await fetch('http://127.0.0.1:8000/api/refresh/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ candidate_names: names }),
        });
      }
      onRefresh();
      setStaleCount(0);
    } catch (err) {
      console.error(err);
    } finally {
      setRefreshing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      active: 'badge-active', pending_consent: 'badge-pending', stale: 'badge-stale',
    };
    return <span className={`badge ${map[status] || 'badge-pending'}`}>{status.replace('_', ' ')}</span>;
  };

  const getOutreachBadge = (status: string) => {
    const map: Record<string, string> = {
      not_contacted: 'badge-pending', email_sent: 'badge-sent',
      replied: 'badge-replied', no_reply: 'badge-no-reply',
    };
    return <span className={`badge ${map[status] || 'badge-pending'}`}>{status.replace('_', ' ')}</span>;
  };

  const seniorities = ['all', ...new Set(candidates.map(c => c.seniority).filter(Boolean))];
  const statuses = ['all', ...new Set(candidates.map(c => c.status).filter(Boolean))];

  return (
    <div className="dashboard">
      <HealthBanner candidates={candidates} />

      {/* View Toggle */}
      <div className="dashboard-view-toggle">
        <button
          className={`toggle-btn ${dashboardView === 'overview' ? 'active' : ''}`}
          onClick={() => setDashboardView('overview')}
        >
          Overview
        </button>
        <button
          className={`toggle-btn ${dashboardView === 'database' ? 'active' : ''}`}
          onClick={() => setDashboardView('database')}
        >
          Talent Database
        </button>
      </div>

      {/* OVERVIEW VIEW */}
      {dashboardView === 'overview' && (
        <div className="dashboard-widgets-grid">
          {/* Active Hiring Requests Widget */}
          <div className="dashboard-widget">
            <div className="widget-header">
              <h3 className="widget-title">Active Hiring Requests</h3>
              {onNavigate && (
                <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('hiring')}>
                  View All
                </button>
              )}
            </div>
            <div className="widget-content">
              {loadingJobs ? (
                <div className="loading-spinner"><span className="spinner"></span></div>
              ) : activeJobs.length > 0 ? (
                <div className="job-list">
                  {activeJobs.map(job => (
                    <div key={job.id} className="job-list-item">
                      <div className="job-info">
                        <div className="job-title">{job.job_title}</div>
                        <div className="job-meta">{job.location}</div>
                      </div>
                      <div className="job-stats">
                        <div className="stat-pill">
                          <span className="stat-val">{job.total_applicants}</span> apps
                        </div>
                        <div className="stat-pill highlight">
                          <span className="stat-val">{job.in_progress}</span> in progress
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state-sm">No active hiring requests.</div>
              )}
            </div>
          </div>

          {/* Pipeline Status Widget */}
          <div className="dashboard-widget">
            <div className="widget-header">
              <h3 className="widget-title">Pipeline Status</h3>
            </div>
            <div className="widget-content pipeline-content">
              <div className="pipeline-stage">
                <div className="stage-name">Applied</div>
                <div className="stage-count">{pipelineStats.applied}</div>
                <div className="stage-bar"><div className="stage-fill" style={{ width: `${Math.min(100, pipelineStats.applied * 5)}%` }}></div></div>
              </div>
              <div className="pipeline-stage">
                <div className="stage-name">Screening</div>
                <div className="stage-count">{pipelineStats.screening}</div>
                <div className="stage-bar"><div className="stage-fill fill-blue" style={{ width: `${Math.min(100, pipelineStats.screening * 10)}%` }}></div></div>
              </div>
              <div className="pipeline-stage">
                <div className="stage-name">Interview</div>
                <div className="stage-count">{pipelineStats.interview}</div>
                <div className="stage-bar"><div className="stage-fill fill-yellow" style={{ width: `${Math.min(100, pipelineStats.interview * 15)}%` }}></div></div>
              </div>
              <div className="pipeline-stage">
                <div className="stage-name">Offer</div>
                <div className="stage-count">{pipelineStats.offer}</div>
                <div className="stage-bar"><div className="stage-fill fill-green" style={{ width: `${Math.min(100, pipelineStats.offer * 30)}%` }}></div></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TALENT DATABASE VIEW */}
      {dashboardView === 'database' && (
        <>
          <div className="section-header">
            <div>
              <div className="section-title">Talent Pool</div>
              <div className="section-subtitle">{candidates.length} candidates in database</div>
            </div>
            <div className="header-actions">
              <button className="btn btn-secondary btn-sm" onClick={handleCheckStale}>
                Check Stale
              </button>
              {staleCount !== null && staleCount > 0 && (
                <button className="btn btn-primary btn-sm" onClick={handleRefreshAll} disabled={refreshing}>
                  {refreshing ? 'Refreshing...' : `Refresh ${staleCount} Stale`}
                </button>
              )}
              {staleCount === 0 && <span className="stale-ok">All up to date</span>}
            </div>
          </div>

          <div className="dashboard-filters">
            <input
              type="text"
              className="form-input search-input"
              placeholder="Search by name, tech, or location..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
            <select className="form-select" value={filterSeniority} onChange={e => setFilterSeniority(e.target.value)}>
              {seniorities.map(s => <option key={s} value={s}>{s === 'all' ? 'All Seniority' : s}</option>)}
            </select>
            <select className="form-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              {statuses.map(s => <option key={s} value={s}>{s === 'all' ? 'All Status' : s.replace('_', ' ')}</option>)}
            </select>
            <span className="filter-count">{filtered.length} results</span>
          </div>

          <div className="table-container">
            <table className="talent-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Seniority</th>
                  <th>Role</th>
                  <th>Location</th>
                  <th>Technologies</th>
                  <th>Experience</th>
                  <th>Status</th>
                  <th>Outreach</th>
                  <th>Links</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c, idx) => (
                  <tr key={idx} className="table-row">
                    <td className="cell-name">
                      <div className="name-avatar">{c.name.split(' ').map(n => n[0]).join('').slice(0, 2)}</div>
                      <div>
                        <div className="name-text">{c.name}</div>
                        {c.email && <div className="name-email">{c.email}</div>}
                      </div>
                    </td>
                    <td><span className="seniority-pill">{c.seniority || '-'}</span></td>
                    <td className="cell-role">{c.current_role || '-'}</td>
                    <td>{c.location || '-'}</td>
                    <td className="cell-tech">
                      <div className="tech-tags">
                        {c.technologies.split(',').slice(0, 4).map((t, i) =>
                          <span key={i} className="tech-tag">{t.trim()}</span>
                        )}
                        {c.technologies.split(',').length > 4 && <span className="tech-more">+{c.technologies.split(',').length - 4}</span>}
                      </div>
                    </td>
                    <td>{c.years_of_experience ? `${c.years_of_experience}y` : '-'}</td>
                    <td>{getStatusBadge(c.status)}</td>
                    <td>{getOutreachBadge(c.outreach_status)}</td>
                    <td className="cell-links">
                      {c.linkedin_url && <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer" className="link-btn" title="LinkedIn">in</a>}
                      {c.github_url && <a href={c.github_url} target="_blank" rel="noopener noreferrer" className="link-btn gh" title="GitHub">gh</a>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-text">No candidates match your filters</div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;
