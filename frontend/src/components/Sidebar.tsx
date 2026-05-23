import React from 'react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-icon">👁️</div>
        <h2>CVision</h2>
      </div>
      <div className="new-chat-btn">+ Conversație Nouă</div>
      <nav className="sidebar-nav">
        <div className="nav-section-title">Recente</div>
        <div className="nav-item active">
          <span className="icon">💬</span> Talent Matcher RAG
        </div>
      </nav>
      <div className="sidebar-footer">
        <div className="status-indicator"></div>
        <span>Connected to Obsidian Vault</span>
      </div>
    </aside>
  );
};

export default Sidebar;