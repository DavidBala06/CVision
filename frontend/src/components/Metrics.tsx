import React, { useState, useEffect } from 'react';
import './Metrics.css';

interface ProviderInfo {
  provider: string;
  display_name: string;
  region: string;
  is_eea: boolean;
  model_id: string;
  notes: string;
  gdpr_warning: string | null;
}

interface EvalCase {
  id: string;
  query: string;
  expected: string[];
  predicted_top_k: string[];
  hits: string[];
  leaks: string[];
  precision_at_k: number;
  recall_at_k: number;
  reciprocal_rank: number;
  hit: boolean;
  negative_leak: boolean;
}

interface LastEvaluation {
  aggregated: {
    k: number;
    total_cases: number;
    hit_rate: number;
    mean_precision_at_k: number;
    mean_recall_at_k: number;
    mrr: number;
    negative_leak_rate: number;
    accuracy: number;
    target_accuracy: number;
    meets_target: boolean;
    passing_cases: number;
  };
  per_case: EvalCase[];
  framework: string;
  run_at?: string;
}

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
  target_accuracy: number;
  evaluation_framework: string;
  llm_provider: ProviderInfo;
  last_evaluation: LastEvaluation | null;
}

const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/metrics');
      if (res.ok) setMetrics(await res.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunEval = async () => {
    setRunning(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/evaluate?k=3', { method: 'POST' });
      if (res.ok) await fetchMetrics();
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(false);
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
          <div className="empty-state-icon">📈</div>
          <div className="empty-state-text">Could not load metrics. Is the backend running?</div>
        </div>
      </div>
    );
  }

  const poolStats = metrics.pool_stats;
  const outreach = metrics.outreach_summary;
  const evalRun = metrics.last_evaluation;
  const targetPct = Math.round(metrics.target_accuracy * 100);
  const accuracyPct = evalRun ? Math.round(evalRun.aggregated.accuracy * 100) : null;

  return (
    <div className="metrics">
      <div className="section-header">
        <div>
          <div className="section-title">📈 Success Metrics & Analytics</div>
          <div className="section-subtitle">Real evaluation, pool health, and GDPR compliance overview</div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={handleRunEval} disabled={running}>
          {running ? <><span className="spinner"></span> Running…</> : '▶️ Run Evaluation'}
        </button>
      </div>

      {/* LLM provider banner */}
      <div className={`provider-banner ${metrics.llm_provider.is_eea ? 'eea-ok' : 'eea-warn'}`}>
        <div className="provider-row">
          <strong>LLM Provider:</strong> {metrics.llm_provider.display_name}
          <span className="provider-region">({metrics.llm_provider.region})</span>
          {metrics.llm_provider.is_eea
            ? <span className="badge badge-active">EEA / GDPR-friendly</span>
            : <span className="badge badge-stale">Outside EEA</span>}
        </div>
        {metrics.llm_provider.gdpr_warning && (
          <div className="provider-warning">⚠️ {metrics.llm_provider.gdpr_warning}</div>
        )}
      </div>

      <div className="metrics-content">
        {/* Real eval results */}
        <div className="metrics-section">
          <h3 className="metrics-section-title">Shortlisting Accuracy ({metrics.evaluation_framework.split('.')[0]})</h3>
          {evalRun ? (
            <>
              <div className="metric-cards">
                <div className="metric-card highlight">
                  <div className="metric-value">{accuracyPct}%</div>
                  <div className="metric-label">Accuracy (passing cases)</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{(evalRun.aggregated.mean_precision_at_k * 100).toFixed(0)}%</div>
                  <div className="metric-label">Precision@{evalRun.aggregated.k}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{(evalRun.aggregated.mean_recall_at_k * 100).toFixed(0)}%</div>
                  <div className="metric-label">Recall@{evalRun.aggregated.k}</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value">{evalRun.aggregated.mrr.toFixed(2)}</div>
                  <div className="metric-label">MRR</div>
                </div>
                <div className="metric-card">
                  <div className="metric-value red">{(evalRun.aggregated.negative_leak_rate * 100).toFixed(0)}%</div>
                  <div className="metric-label">Negative Leak Rate</div>
                </div>
              </div>
              <div className="accuracy-bar-container">
                <div className="accuracy-info">
                  <span className="accuracy-label">
                    Target: {targetPct}% | Current: {accuracyPct}% {evalRun.aggregated.meets_target ? '✅' : '❌'}
                  </span>
                  <span className="accuracy-framework">
                    {evalRun.aggregated.passing_cases}/{evalRun.aggregated.total_cases} cases passed —
                    last run {evalRun.run_at ? new Date(evalRun.run_at).toLocaleString() : 'unknown'}
                  </span>
                </div>
                <div className="accuracy-bar">
                  <div
                    className="accuracy-fill"
                    style={{ width: `${accuracyPct}%`, background: evalRun.aggregated.meets_target ? undefined : '#e74c3c' }}
                  ></div>
                </div>
              </div>

              {/* Per-case detail (failing cases highlighted) */}
              <details className="eval-detail">
                <summary>Per-case breakdown ({evalRun.per_case.length} cases)</summary>
                <table className="talent-table">
                  <thead>
                    <tr>
                      <th>Case</th>
                      <th>Query</th>
                      <th>Expected</th>
                      <th>Got (top {evalRun.aggregated.k})</th>
                      <th>P@k</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evalRun.per_case.map(c => (
                      <tr key={c.id} className={c.hit && !c.negative_leak ? '' : 'eval-row-fail'}>
                        <td>{c.id}</td>
                        <td className="cell-role">{c.query}</td>
                        <td>{c.expected.join(', ')}</td>
                        <td>{c.predicted_top_k.join(', ') || '—'}</td>
                        <td>{c.precision_at_k.toFixed(2)}</td>
                        <td>
                          {c.hit && !c.negative_leak
                            ? <span className="badge badge-active">PASS</span>
                            : c.negative_leak
                              ? <span className="badge badge-stale">LEAK</span>
                              : <span className="badge badge-no-reply">MISS</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            </>
          ) : (
            <div className="info-msg">
              No evaluation has been run yet. Click "Run Evaluation" above to compute precision/recall/MRR
              against <code>backend/evals/ground_truth.json</code>.
            </div>
          )}
        </div>

        {/* Pool health */}
        <div className="metrics-section">
          <h3 className="metrics-section-title">Talent Pool Health</h3>
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
              <div className="metric-label">Stale (&gt;6 months)</div>
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
          <h3 className="metrics-section-title">GDPR &amp; Security Posture</h3>
          <div className="gdpr-card">
            <div className="gdpr-item">✅ CSV + vector DB stored locally — no external persistence</div>
            <div className="gdpr-item">✅ PII (emails) masked by default in /api/candidates; reveal logged in audit</div>
            <div className="gdpr-item">✅ Consent tracking per candidate (active / pending_consent)</div>
            <div className="gdpr-item">✅ Human-in-the-Loop: extraction, refresh, and outreach all require human approval</div>
            <div className="gdpr-item">✅ Prompt-injection guardrails (regex + homoglyph/whitespace normalization)</div>
            <div className="gdpr-item">✅ JSON output validation — sensitive fields stripped before response</div>
            <div className="gdpr-item">✅ Audit log: every state change is appended to <code>data/audit.jsonl</code></div>
            <div className="gdpr-item">🚫 Agent never sends emails or contacts candidates autonomously</div>
            {!metrics.llm_provider.is_eea && (
              <div className="gdpr-item warn">⚠️ Current LLM provider is outside the EEA — see banner above</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Metrics;
