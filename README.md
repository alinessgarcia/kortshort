# KortShort (Klap.app Clone) 🎬⚡

Um clone open-source profissional do Klap.app. Transforma vídeos longos (16:9) do YouTube em **múltiplos shorts verticais (9:16)** para TikTok, Reels e Shorts usando IA local.

## 🚀 Como Rodar

### Pré-requisitos
- **Node.js** (v18+)
- **Python** (v3.10+)
- **FFmpeg** (auto-detectado do projeto mp3ok, ou instalar globalmente)

### 1. Frontend (React + Vite)
```bash
cd kortshort
npm install
npm run dev
# → http://localhost:5173
```

### 2. Backend (Python + FastAPI)
```powershell
cd kortshort/backend
pip install fastapi uvicorn yt-dlp pydantic python-multipart
$env:PYTHONIOENCODING="utf-8"; python main.py
# → http://localhost:8000
```

## 📦 Stack Tecnológico

| Camada | Tecnologia |
|---|---|
| **Frontend** | React 19 + Vite 8 + Vanilla CSS |
| **Backend** | Python + FastAPI + yt-dlp + FFmpeg |
| **Database** | SQLite (kortshort.db) |
| **Progress** | Server-Sent Events (SSE) |

## ✅ Funcionalidades Implementadas

### Sprint 1 — Visual Premium
- [x] Landing page com hero, social proof, features grid
- [x] Design system com glassmorphism e gradientes
- [x] Sidebar com branding KortShort
- [x] Input pill-shaped com botão Generate
- [x] Micro-animações e hover effects
- [x] Layout responsivo mobile

### Sprint 2 — Backend Funcional
- [x] Múltiplos clips por vídeo (3-4 clips automáticos)
- [x] Cálculo inteligente de segmentos baseado na duração
- [x] Progresso em tempo real via SSE
- [x] Persistência com SQLite (histórico de projetos)
- [x] Thumbnails automáticos via FFmpeg
- [x] Upload de arquivo local (`POST /upload`)
- [x] API de histórico (`GET /history`, `DELETE /history/:id`)
- [x] Auto-detecção do FFmpeg em paths conhecidos
- [x] Player de vídeo integrado com Download/Copy

## 🛣️ Roadmap — Próximos Sprints

### Sprint 3 — IA Local 🧠
- [ ] Whisper Large: transcrição + legendas animadas word-by-word
- [ ] Ollama/Qwen: curadoria inteligente de momentos virais
- [ ] OpenCV: smart reframe com rastreamento facial

### Sprint 4 — Polimento 💎
- [ ] React Router para navegação real
- [ ] Settings page (modelo Whisper, Ollama, duração)
- [ ] Export multi-formato (TikTok, Reels, Shorts)
- [ ] Batch processing (múltiplos vídeos)

## 🔧 API Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/process` | Processa URL do YouTube → múltiplos clips |
| `POST` | `/upload` | Upload de arquivo local → múltiplos clips |
| `GET` | `/progress/:id` | SSE stream de progresso |
| `GET` | `/history` | Lista projetos com shorts |
| `DELETE` | `/history/:id` | Remove projeto |
| `GET` | `/health` | Status do sistema (FFmpeg, DB) |

## 📄 Licença
MIT — Use, modifique e distribua livremente.
