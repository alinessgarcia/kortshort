import React from 'react';
import { Home, Video, Settings, CreditCard, Plus, Zap } from 'lucide-react';

export default function Sidebar({ onNavigate, currentPage }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">K</div>
        KortShort
      </div>

      <button className="new-project-btn" onClick={() => onNavigate && onNavigate('generate')}>
        <Plus size={16} /> New Project
      </button>

      <div className="nav-section">
        <div className="nav-label">Overview</div>
        <a href="#" className={`nav-item ${currentPage === 'home' ? 'active' : ''}`}
           onClick={(e) => { e.preventDefault(); onNavigate && onNavigate('home'); }}>
          <Home size={18} /> Home
        </a>
        <a href="#" className={`nav-item ${currentPage === 'videos' ? 'active' : ''}`}
           onClick={(e) => { e.preventDefault(); onNavigate && onNavigate('videos'); }}>
          <Video size={18} /> My Videos
        </a>
      </div>

      <div className="nav-section">
        <div className="nav-label">Account</div>
        <a href="#" className="nav-item">
          <Settings size={18} /> Settings
        </a>
        <a href="#" className="nav-item">
          <CreditCard size={18} /> Billing
        </a>
      </div>

      <div className="sidebar-spacer"></div>

      <div className="user-profile">
        <div className="avatar">A</div>
        <div className="user-info">
          <span className="user-name">My Workspace</span>
          <span className="user-credits"><Zap size={12} style={{display:'inline', verticalAlign:'middle'}} /> Unlimited</span>
        </div>
      </div>
    </aside>
  );
}
