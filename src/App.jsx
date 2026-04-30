import React from 'react';
import Sidebar from './components/Sidebar';
import MainContent from './components/MainContent';
import './index.css';

function App() {
  return (
    <div className="app-container">
      <Sidebar />
      <MainContent />
    </div>
  );
}

export default App;
