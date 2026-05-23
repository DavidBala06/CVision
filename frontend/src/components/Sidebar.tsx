import React from 'react';
import { Search, CircleUserRound, MoreHorizontal } from 'lucide-react';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-area">
          <div className="logo-icon">TM</div>
          <div className="logo-text">
            <h1>TalentAI</h1>
            <span>v1.0 · MVP</span>
          </div>
        </div>
        <button className="new-chat-btn">
          <Search size={18} />
          <span>New search</span>
        </button>
        <div className="search-bar">
          <Search size={16} className="search-icon" />
          <input type="text" placeholder="Search candidates..." />
        </div>
      </div>

      <div className="sidebar-content">
        <h2 className="section-title">MENU</h2>
        <ul className="history-list">
          <li className="history-item active">
            <div className="item-title">Dashboard</div>
          </li>
          <li className="history-item">
            <div className="item-title">Candidates Pool</div>
          </li>
          <li className="history-item">
            <div className="item-title">Job Postings</div>
          </li>
          <li className="history-item">
            <div className="item-title">Settings</div>
          </li>
        </ul>
      </div>

      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">
            <CircleUserRound size={32} color="var(--accent-purple-light)" strokeWidth={1.5} />
          </div>
          <div className="user-info">
            <span className="user-name">Claudia Popescu</span>
            <span className="user-role">Talent Manager</span>
          </div>
          <button className="user-menu-btn">
            <MoreHorizontal size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
