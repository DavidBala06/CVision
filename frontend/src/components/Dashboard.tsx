import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import type { PoolCandidate } from '../App';
import HealthBanner from './HealthBanner';
import PendingActions from './PendingActions';

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
  const [activeJobs, setActiveJobs] = useState<HiringRequestSummary[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  useEffect(() => {
    fetchActiveJobs();
  }, []);

  const fetchActiveJobs = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/hiring-requests');
      if (res.ok) {
        const data = await res.json();
        // Filter only open jobs and take top 5
        const openJobs = data.filter((j: HiringRequestSummary) => j.status === 'open').slice(0, 5);
        setActiveJobs(openJobs);
      }
    } catch (err) {
      console.error('Failed to fetch active jobs:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  // Calculate pipeline status from all applications
  const [pipelineStats, setPipelineStats] = useState({
    applied: 0,
    screening: 0,
    interview: 0,
    offer: 0
  });

  useEffect(() => {
    const fetchAllApplications = async () => {
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

    fetchAllApplications();
  }, []);

  return (
    <div className="dashboard">
      <HealthBanner candidates={candidates} />
      
      <PendingActions onNavigate={onNavigate} />

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
    </div>
  );
};

export default Dashboard;
