import React, { useState } from 'react';
import { Link, Upload, Play, MonitorPlay } from 'lucide-react';

export default function MainContent() {
  const [url, setUrl] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = React.useRef(null);

  const handleGenerate = async () => {
    if(!url) return;
    setIsProcessing(true);
    
    try {
      const response = await fetch('http://localhost:8000/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
      });
      
      const data = await response.json();
      
      if(data.status === 'success') {
        alert('Vídeo gerado com sucesso! Link: ' + data.video_url);
        // You could also set this URL to a state to display the video in the UI
      } else {
        alert('Erro ao processar: ' + data.detail);
      }
    } catch (error) {
      alert('Erro de conexão com o servidor local.');
    } finally {
      setIsProcessing(false);
      setUrl('');
    }
  };

  return (
    <main className="main-content">
      <div className="top-header">
        <div className="credits-badge">
          <span>⚡</span> 10 Credits
        </div>
      </div>

      <div className="content-wrapper">
        <div className="hero-section">
          <h1 className="hero-title">Create viral shorts in a click</h1>
          <p className="hero-subtitle">Paste a YouTube or TikTok link to get started.</p>
        </div>

        <div className="generator-box">
          {isProcessing && (
            <div className="processing-overlay">
              <div className="spinner"></div>
              <div className="processing-text">Analyzing video...</div>
            </div>
          )}
          
          <div className="input-container">
            <div className="input-group">
              <Link className="url-icon" size={20} />
              <input 
                type="text" 
                className="url-input" 
                placeholder="Paste YouTube, TikTok or URL here..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
            </div>
            
            <button className="generate-btn" onClick={handleGenerate}>
              Generate Shorts
              <MonitorPlay size={18} />
            </button>
          </div>

          <div className="upload-area" onClick={() => fileInputRef.current?.click()}>
            <Upload className="upload-icon" size={20} />
            <div className="upload-text">Or click here to upload a local file</div>
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              accept="video/*"
              onChange={(e) => {
                if(e.target.files && e.target.files[0]) {
                  alert(`Arquivo selecionado: ${e.target.files[0].name}. (Backend local file upload pendente)`);
                }
              }}
            />
          </div>
        </div>

        <div className="projects-section">
          <h2 className="section-title">Recent Videos</h2>
          <div className="projects-grid">
            {[1, 2, 3].map((item) => (
              <div className="project-card" key={item}>
                <div className="project-thumbnail">
                  <Play className="play-icon" size={32} />
                </div>
                <div className="project-info">
                  <div className="project-title">Podcast Episode #{item} - How to go viral</div>
                  <div className="project-meta">
                    <span>{item * 4} Shorts generated</span>
                    <span>2 days ago</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
