import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import './index.css';

function App() {
  const [view, setView] = useState('landing'); // 'landing' | 'dashboard'
  const [initialUrl, setInitialUrl] = useState('');
  const [currentPage, setCurrentPage] = useState('home');

  const enterDashboard = (url) => {
    setInitialUrl(url || '');
    setView('dashboard');
  };

  if (view === 'landing') {
    return <LandingPage onEnterDashboard={enterDashboard} />;
  }

  return (
    <div className="app-container">
      <Sidebar onNavigate={setCurrentPage} currentPage={currentPage} />
      <MainContent initialUrl={initialUrl} />
    </div>
  );
}

export default App;
