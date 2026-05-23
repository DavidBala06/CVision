import React from 'react';
import './Sidebar.css';

type TabId = 'dashboard' | 'shortlist' | 'upload' | 'outreach' | 'linkedin' | 'metrics';

interface SidebarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  candidateCount: number;
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

      <div className="sidebar-footer">
        <div className="status-indicator"></div>
        <span>Connected to Talent Pool CSV</span>
      </div>
    </aside>
  );
};

export default Sidebar;