import React from 'react';
import { Video, FolderOpen, Settings, Home, CreditCard } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
        </div>
        Klap
      </div>

      <div className="nav-section">
        <div className="nav-label">Overview</div>
        <a href="#" className="nav-item active">
          <Home size={18} />
          Home
        </a>
        <a href="#" className="nav-item">
          <Video size={18} />
          My Videos
        </a>
      </div>

      <div className="nav-section">
        <div className="nav-label">Settings</div>
        <a href="#" className="nav-item">
          <Settings size={18} />
          Account
        </a>
        <a href="#" className="nav-item">
          <CreditCard size={18} />
          Billing
        </a>
      </div>

      <div className="sidebar-spacer"></div>

      <div className="user-profile">
        <div className="avatar"></div>
        <div className="user-info">
          <span className="user-name">My Workspace</span>
          <span className="user-credits">10 credits</span>
        </div>
      </div>
    </aside>
  );
}
