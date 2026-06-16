import React, { useEffect, useState } from 'react';
import './PendingActions.css';

interface PendingAction {
  type: string;
  priority: 'high' | 'medium' | 'low';
  count: number;
  candidates: string[];
  message: string;
}

interface PendingActionsProps {
  onNavigate?: (tab: string) => void;
}

const ACTION_CONFIG: Record<string, { icon: string; iconClass: string; actionLabel: string; targetTab: string }> = {
  stale_profiles: { icon: '🔄', iconClass: 'icon-stale', actionLabel: 'Refresh Profiles', targetTab: 'dashboard' },
  follow_up_needed: { icon: '📩', iconClass: 'icon-followup', actionLabel: 'View Outreach', targetTab: 'outreach' },
  new_applications: { icon: '📋', iconClass: 'icon-new', actionLabel: 'Review Candidates', targetTab: 'dashboard' },
};

const PendingActions: React.FC<PendingActionsProps> = ({ onNavigate }) => {
  const [actions, setActions] = useState<PendingAction[]>([]);
  const [totalActions, setTotalActions] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetchActions();
  }, []);

  const fetchActions = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/pending-actions');
      if (res.ok) {
        const data = await res.json();
        setActions(data.actions || []);
        setTotalActions(data.total_actions || 0);
      }
    } catch (err) {
      console.error('Failed to fetch pending actions:', err);
    } finally {
      setLoaded(true);
    }
  };

  if (!loaded) return null;

  return (
    <div className="pending-actions">
      <div className="pending-actions-header">
        <div className="pending-actions-title">
          Pending Actions
          <span className={`pending-actions-badge ${totalActions === 0 ? 'zero' : ''}`}>
            {totalActions}
          </span>
        </div>
      </div>

      {actions.length === 0 ? (
        <div className="actions-clear">
          <span className="actions-clear-icon">✓</span>
          All caught up — no pending actions right now.
        </div>
      ) : (
        <div className="actions-grid">
          {actions.map((action) => {
            const config = ACTION_CONFIG[action.type] || {
              icon: '📌',
              iconClass: 'icon-new',
              actionLabel: 'View',
              targetTab: 'dashboard',
            };

            return (
              <div
                key={action.type}
                className={`action-card priority-${action.priority}`}
              >
                <div className={`action-icon ${config.iconClass}`}>
                  {config.icon}
                </div>
                <div className="action-content">
                  <div className={`action-count count-${action.priority}`}>
                    {action.count}
                  </div>
                  <div className="action-message">{action.message}</div>
                  {action.candidates.length > 0 && (
                    <div className="action-names">
                      {action.candidates.join(', ')}
                    </div>
                  )}
                  <button
                    className="action-btn"
                    onClick={() => onNavigate?.(config.targetTab)}
                  >
                    {config.actionLabel} →
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PendingActions;
