import React, { useState, useEffect } from 'react';
import './Metrics.css';

interface MetricsData {
  pool_stats: {
    total: number;
    active: number;
    pending_consent: number;
    stale: number;
    seniority_distribution: Record<string, number>;
    location_distribution: Record<string, number>;
  };
  outreach_summary: Record<string, number>;
  target_accuracy: string;
  evaluation_framework: string;
}

const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/metrics');
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="metrics">
        <div className="loading-spinner"><span className="spinner"></span> Loading metrics...</div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="metrics">
        <div className="empty-state">
          <div className="empty-state-icon"></div>
          <div className="empty-state-text">Could not load metrics. Is the backend running?</div>
        </div>
      </div>
    );
  }

  const poolStats = metrics.pool_stats;
  const outreach = metrics.outreach_summary;

  return (
    <div className="metrics">
      <div className="section-header">
        <div>
          <div className="section-title">Analytics</div>
          <div className="section-subtitle">Pool health, hiring funnel & compliance overview</div>
        </div>
      </div>

      <div className="metrics-content">
        {/* Pool health cards */}
        <div className="metrics-section">
          <h3 className="metrics-section-title">Pool Overview</h3>
          <div className="metric-cards">
            <div className="metric-card highlight">
              <div className="metric-value">{poolStats.total}</div>
              <div className="metric-label">Total Candidates</div>
            </div>
            <div className="metric-card">
              <div className="metric-value green">{poolStats.active}</div>
              <div className="metric-label">Active (Consent)</div>
            </div>
            <div className="metric-card">
              <div className="metric-value yellow">{poolStats.pending_consent}</div>
              <div className="metric-label">Pending Consent</div>
            </div>
            <div className="metric-card">
              <div className="metric-value red">{poolStats.stale}</div>
              <div className="metric-label">Stale (&gt;3 months)</div>
            </div>
          </div>
        </div>


        {/* Outreach funnel */}
        <div className="metrics-section">
          <h3 className="metrics-section-title">Outreach Funnel</h3>
          <div className="metric-cards">
            {Object.entries(outreach).map(([status, count]) => (
              <div key={status} className="metric-card small">
                <div className="metric-value">{count}</div>
                <div className="metric-label">{status.replace('_', ' ')}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Distributions */}
        <div className="distributions">
          <div className="metrics-section">
            <h3 className="metrics-section-title">Seniority Distribution</h3>
            <div className="dist-bars">
              {Object.entries(poolStats.seniority_distribution || {}).sort((a, b) => b[1] - a[1]).map(([level, count]) => (
                <div key={level} className="dist-row">
                  <span className="dist-label">{level}</span>
                  <div className="dist-bar-bg">
                    <div className="dist-bar-fill" style={{ width: `${(count / poolStats.total) * 100}%` }}></div>
                  </div>
                  <span className="dist-count">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="metrics-section">
            <h3 className="metrics-section-title">Location Distribution</h3>
            <div className="dist-bars">
              {Object.entries(poolStats.location_distribution || {}).sort((a, b) => b[1] - a[1]).map(([loc, count]) => (
                <div key={loc} className="dist-row">
                  <span className="dist-label">{loc}</span>
                  <div className="dist-bar-bg">
                    <div className="dist-bar-fill green" style={{ width: `${(count / poolStats.total) * 100}%` }}></div>
                  </div>
                  <span className="dist-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* GDPR compliance card */}
        <div className="metrics-section">
          <h3 className="metrics-section-title">GDPR Compliance</h3>
          <div className="gdpr-card">
            <div className="gdpr-item">All data stored locally (PostgreSQL database)</div>
            <div className="gdpr-item">Consent tracking per candidate (active / pending_consent)</div>
            <div className="gdpr-item">Data retention: 12 months (CV), 3 months (scrape)</div>
            <div className="gdpr-item">Human-in-the-Loop: all actions require HR approval</div>
            <div className="gdpr-item">Prompt injection guardrails active</div>
            <div className="gdpr-item">No external communication — recommendations only</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Metrics;
