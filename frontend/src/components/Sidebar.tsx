import React, { useEffect, useState } from 'react';
import './Sidebar.css';

type TabId = 'dashboard' | 'shortlist' | 'upload' | 'outreach' | 'linkedin' | 'metrics';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  candidateCount: number;
}

interface ProviderInfo {
  display_name: string;
  region: string;
  is_eea: boolean;
}

const navItems: { id: TabId; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Talent Pool', icon: '📊' },
  { id: 'shortlist', label: 'Shortlist AI', icon: '🎯' },
  { id: 'upload', label: 'Upload CV', icon: '📄' },
  { id: 'outreach', label: 'Outreach', icon: '✉️' },
  { id: 'linkedin', label: 'LinkedIn Search', icon: '🔍' },
  { id: 'metrics', label: 'Metrics', icon: '📈' },
];

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, candidateCount }) => {
  const [provider, setProvider] = useState<ProviderInfo | null>(null);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/provider')
      .then(r => r.ok ? r.json() : null)
      .then(setProvider)
      .catch(() => {});
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">🧠</div>
        <div>
          <h2>TalentAI</h2>
          <span className="logo-subtitle">by CVision</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Modules</div>
        {navItems.map(item => (
          <div
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <span className="icon">{item.icon}</span>
            {item.label}
          </div>
        ))}
      </nav>

      <div className="sidebar-stats">
        <div className="stat-item">
          <span className="stat-value">{candidateCount}</span>
          <span className="stat-label">Candidates</span>
        </div>
      </div>

      {provider && (
        <div className={`sidebar-provider ${provider.is_eea ? 'eea' : 'non-eea'}`} title={provider.display_name}>
          <div className="provider-dot"></div>
          <div className="provider-text">
            <div className="provider-name">{provider.display_name}</div>
            <div className="provider-region">{provider.region} {provider.is_eea ? '✓ EEA' : '⚠ non-EEA'}</div>
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        <div className="status-indicator"></div>
        <span>Local CSV · HITL · audit-logged</span>
      </div>
    </aside>
  );
};

export default Sidebar;
