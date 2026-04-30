import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link, Upload, Play, MonitorPlay, Download, Copy, Zap, Trash2, Clock, CheckCircle } from 'lucide-react';

const API = 'http://localhost:8000';

export default function MainContent({ initialUrl }) {
  const [url, setUrl] = useState(initialUrl || '');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ step: '', progress: 0 });
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const fileInputRef = useRef(null);

  // Load history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API}/history`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch {}
  };

  const listenProgress = useCallback((projectId) => {
    const evtSource = new EventSource(`${API}/progress/${projectId}`);
    evtSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setProgress(data);
      if (data.status === 'done' || data.status === 'error') {
        evtSource.close();
      }
    };
    evtSource.onerror = () => evtSource.close();
  }, []);

  const stepLabels = {
    downloading: '📥 Downloading video...',
    uploading: '📤 Uploading file...',
    analyzing: '📊 Analyzing video...',
    cutting: '✂️ Generating clips...',
    done: '✅ Done!',
    error: '❌ Error occurred'
  };

  const handleGenerate = async () => {
    if (!url) return;
    setIsProcessing(true);
    setError('');
    setResults([]);
    setProgress({ step: 'downloading', progress: 5 });

    try {
      const response = await fetch(`${API}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setProgress({ step: 'done', progress: 100 });
        setResults(data.clips.map((c, i) => ({
          id: `${data.project_id}_${i}`,
          url: c.video_url,
          thumbnail: c.thumbnail_url,
          title: `Clip ${i + 1} — ${data.title}`,
          duration: `${Math.round(c.duration)}s`,
          start: `${Math.round(c.start)}s`,
        })));
        if (data.project_id) listenProgress(data.project_id);
        fetchHistory();
      } else {
        setError(data.detail || 'Processing failed');
      }
    } catch (err) {
      setError('Cannot connect to backend. Run: python backend/main.py');
    } finally {
      setTimeout(() => setIsProcessing(false), 800);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsProcessing(true);
    setError('');
    setResults([]);
    setProgress({ step: 'uploading', progress: 5 });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API}/upload`, { method: 'POST', body: formData });
      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setProgress({ step: 'done', progress: 100 });
        setResults(data.clips.map((c, i) => ({
          id: `${data.project_id}_${i}`,
          url: c.video_url,
          thumbnail: c.thumbnail_url,
          title: `Clip ${i + 1} — ${data.title}`,
          duration: `${Math.round(c.duration)}s`,
          start: `${Math.round(c.start)}s`,
        })));
        fetchHistory();
      } else {
        setError(data.detail || 'Upload failed');
      }
    } catch {
      setError('Upload failed. Check backend.');
    } finally {
      setTimeout(() => setIsProcessing(false), 800);
    }
  };

  const deleteProject = async (id) => {
    try {
      await fetch(`${API}/history/${id}`, { method: 'DELETE' });
      setHistory(prev => prev.filter(p => p.id !== id));
    } catch {}
  };

  const copyLink = (videoUrl, id) => {
    navigator.clipboard.writeText(videoUrl);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatTime = (isoStr) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return isoStr; }
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
          <p className="hero-subtitle">Paste a YouTube link or upload a local file. AI generates multiple clips automatically.</p>
        </div>

        {/* Generator Box */}
        <div className="generator-box">
          {isProcessing && (
            <div className="processing-overlay">
              <div className="spinner"></div>
              <div className="processing-text">
                {stepLabels[progress.step] || 'Processing...'}
              </div>
              {progress.total_clips && (
                <div className="processing-detail">
                  Clip {progress.current_clip || '...'} of {progress.total_clips}
                </div>
              )}
              <div className="progress-bar-wrapper">
                <div className="progress-bar" style={{ width: `${progress.progress || 0}%` }}></div>
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
                disabled={isProcessing}
              />
            </div>
            <button className="generate-btn" onClick={handleGenerate} disabled={isProcessing}>
              <span>✨</span> Generate
              <MonitorPlay size={18} />
            </button>
          </div>

          <div className="upload-area" onClick={() => !isProcessing && fileInputRef.current?.click()}>
            <Upload className="upload-icon" size={20} />
            <div className="upload-text">Or drag & drop a local video file here</div>
            <input type="file" ref={fileInputRef} style={{ display: 'none' }} accept="video/*" onChange={handleFileUpload} />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="error-banner">
            <span>❌</span> {error}
            <button onClick={() => setError('')}>✕</button>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h3>Generated Shorts</h3>
              <span className="results-count">
                <CheckCircle size={14} /> {results.length} clip{results.length > 1 ? 's' : ''}
              </span>
            </div>
            <div className="results-grid">
              {results.map((r) => (
                <div className="result-card" key={r.id}>
                  <div className="result-video">
                    <video src={r.url} controls preload="metadata" poster={r.thumbnail} />
                  </div>
                  <div className="result-info">
                    <div className="result-title">{r.title}</div>
                    <div className="result-meta">
                      <Clock size={11} /> {r.duration} • starts at {r.start}
                    </div>
                  </div>
                  <div className="result-actions">
                    <button onClick={() => window.open(r.url, '_blank')}>
                      <Download size={12} /> Download
                    </button>
                    <button onClick={() => copyLink(r.url, r.id)}>
                      {copiedId === r.id ? <><CheckCircle size={12} /> Copied!</> : <><Copy size={12} /> Copy</>}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* History */}
        <div className="projects-section">
          <h2 className="section-title">Recent Projects</h2>
          {history.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎬</div>
              <h3>No projects yet</h3>
              <p>Generate your first shorts to see them here.</p>
            </div>
          ) : (
            <div className="projects-grid">
              {history.map((project) => (
                <div className="project-card" key={project.id}>
                  <div className="project-thumbnail">
                    {project.clips?.[0]?.thumbnail_url ? (
                      <img src={project.clips[0].thumbnail_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <Play className="play-icon" size={32} />
                    )}
                    <span className="clip-count-badge">
                      {project.clips?.length || 0} clip{(project.clips?.length || 0) !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div className="project-info">
                    <div className="project-title">{project.title}</div>
                    <div className="project-meta">
                      <span className={`status-dot ${project.status}`}></span>
                      <span>{project.status}</span>
                      <span>{formatTime(project.created_at)}</span>
                    </div>
                  </div>
                  <div className="project-actions">
                    <button className="delete-btn" onClick={(e) => { e.stopPropagation(); deleteProject(project.id); }}>
                      <Trash2 size={14} />
                    </button>
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
