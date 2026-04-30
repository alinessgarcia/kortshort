import React, { useState, useRef } from 'react';
import { Link, Upload, Play, MonitorPlay, Download, Copy, Zap } from 'lucide-react';

export default function MainContent({ initialUrl }) {
  const [url, setUrl] = useState(initialUrl || '');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);
  const fileInputRef = useRef(null);

  const steps = [
    '📥 Downloading video...',
    '✂️ Cropping to 9:16...',
    '🎨 Applying filters...',
    '✅ Done!'
  ];

  const handleGenerate = async () => {
    if (!url) return;
    setIsProcessing(true);
    setCurrentStep(0);
    setResults([]);

    try {
      // Simulate progress steps
      const stepInterval = setInterval(() => {
        setCurrentStep(prev => {
          if (prev < steps.length - 1) return prev + 1;
          clearInterval(stepInterval);
          return prev;
        });
      }, 2000);

      const response = await fetch('http://localhost:8000/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      clearInterval(stepInterval);
      const data = await response.json();

      if (data.status === 'success') {
        setCurrentStep(steps.length - 1);
        const newResult = {
          id: Date.now(),
          url: data.video_url,
          title: `Short from ${url.substring(0, 40)}...`,
          duration: '15s',
          createdAt: new Date().toLocaleString()
        };
        setResults([newResult]);
        setHistory(prev => [newResult, ...prev]);
      } else {
        alert('Error: ' + (data.detail || 'Unknown error'));
      }
    } catch (error) {
      alert('Cannot connect to backend. Make sure Python server is running on port 8000.');
    } finally {
      setTimeout(() => setIsProcessing(false), 500);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setCurrentStep(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (data.status === 'success') {
        setCurrentStep(steps.length - 1);
        const newResult = {
          id: Date.now(),
          url: data.video_url,
          title: `Short from ${file.name}`,
          duration: '15s',
          createdAt: new Date().toLocaleString()
        };
        setResults([newResult]);
        setHistory(prev => [newResult, ...prev]);
      }
    } catch (error) {
      alert('Upload failed. Check backend server.');
    } finally {
      setTimeout(() => setIsProcessing(false), 500);
    }
  };

  const copyLink = (videoUrl) => {
    navigator.clipboard.writeText(videoUrl);
  };

  return (
    <main className="main-content">
      <div className="top-header">
        <div className="credits-badge">
          <Zap size={14} /> Unlimited — Local Mode
        </div>
      </div>

      <div className="content-wrapper">
        <div className="hero-section">
          <h1 className="hero-title">Create viral shorts in a click</h1>
          <p className="hero-subtitle">Paste a YouTube link or upload a local file to generate shorts.</p>
        </div>

        {/* Generator Box */}
        <div className="generator-box">
          {isProcessing && (
            <div className="processing-overlay">
              <div className="spinner"></div>
              <div className="processing-text">Processing your video...</div>
              <div className="processing-steps">
                {steps.map((step, i) => (
                  <div key={i} className={`processing-step ${i === currentStep ? 'active' : ''} ${i < currentStep ? 'done' : ''}`}>
                    {step}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="input-container">
            <div className="input-group">
              <Link className="url-icon" size={20} />
              <input
                type="text"
                className="url-input"
                placeholder="Paste YouTube, TikTok or any video URL..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              />
            </div>
            <button className="generate-btn" onClick={handleGenerate}>
              <span>✨</span> Generate
              <MonitorPlay size={18} />
            </button>
          </div>

          <div className="upload-area" onClick={() => fileInputRef.current?.click()}>
            <Upload className="upload-icon" size={20} />
            <div className="upload-text">Or drag & drop a local video file here</div>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="video/*"
              onChange={handleFileUpload}
            />
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h3>Generated Shorts</h3>
              <span className="results-count">{results.length} short{results.length > 1 ? 's' : ''}</span>
            </div>
            <div className="results-grid">
              {results.map((r) => (
                <div className="result-card" key={r.id}>
                  <div className="result-video">
                    <video src={r.url} controls preload="metadata" />
                  </div>
                  <div className="result-info">
                    <div className="result-title">{r.title}</div>
                    <div className="result-meta">{r.duration} • {r.createdAt}</div>
                  </div>
                  <div className="result-actions">
                    <button onClick={() => window.open(r.url, '_blank')}>
                      <Download size={12} /> Download
                    </button>
                    <button onClick={() => copyLink(r.url)}>
                      <Copy size={12} /> Copy Link
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* History */}
        <div className="projects-section">
          <h2 className="section-title">Recent Videos</h2>
          {history.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎬</div>
              <h3>No videos yet</h3>
              <p>Generate your first short to see it here.</p>
            </div>
          ) : (
            <div className="projects-grid">
              {history.map((item) => (
                <div className="project-card" key={item.id}>
                  <div className="project-thumbnail">
                    <Play className="play-icon" size={32} />
                  </div>
                  <div className="project-info">
                    <div className="project-title">{item.title}</div>
                    <div className="project-meta">
                      <span>{item.duration}</span>
                      <span>{item.createdAt}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
