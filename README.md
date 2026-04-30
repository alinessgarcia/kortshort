# KortShort (Klap.app Clone) 🎬⚡

Um clone open-source profissional e minimalista do Klap.app. Este projeto é projetado para transformar vídeos longos (16:9) do YouTube em vídeos curtos e verticais (9:16) para TikTok, Reels e Shorts usando Inteligência Artificial local.

## 🛠️ Stack Tecnológico
O projeto está dividido em duas partes perfeitamente desacopladas:

1. **Front-end (A Casca Premium):**
   - **Framework:** React + Vite
   - **Estilização:** Vanilla CSS (CSS Puro, com foco em responsividade e Light Mode, design minimalista e glassmorphism).
   - **Ícones:** `lucide-react` para iconografia profissional.
   - O painel emula com perfeição o painel do Klap, possuindo Sidebar de navegação, campo inteligente de URL, e uma grade (Grid) mostrando vídeos processados.

2. **Back-end (O Motor de Processamento):**
   - **Framework:** Python + FastAPI
   - **Download de Vídeos:** `yt-dlp` (para extrair os vídeos diretamente da nuvem).
   - **Edição Autônoma:** `FFmpeg` via subprocessos. Atualmente configurado com a equação de crop `crop=ih*9/16:ih` para centralizar a imagem e forçar o corte vertical.

## 🚀 Status Atual (MVP Funcional)
O que o projeto já é capaz de fazer no seu estágio atual:
* Recebe links pelo Front-end (http://localhost:5174).
* Comunica via requisição POST (CORS habilitado) com a API Python local (`http://localhost:8000/process`).
* Baixa o vídeo utilizando o yt-dlp para a pasta oculta `downloads/`.
* Corta e formata para celular os primeiros 15 segundos do vídeo.
* Salva e expõe estaticamente o novo Short gerado na pasta `public/outputs/`.

## 🔮 Roadmap para a IA que assumir o projeto
A base estrutural está perfeita. Para transformar isso num Klap 100% autônomo e de alta inteligência, o(a) próximo(a) desenvolvedor(a) de IA deve seguir a trilha abaixo:

1. **Integração com Whisper (Legendas Automáticas):**
   - Utilizar a instalação local do modelo **Whisper Large** do usuário.
   - Ler o arquivo de áudio extraído, obter a minutagem exata de cada palavra (word-level timestamps) e desenhar as legendas dinâmicas no vídeo pelo FFmpeg (usando filtros de texto ou arquivos `.ass`).

2. **Curadoria Semântica (Ollama + Qwen 3.5 9B):**
   - Extrair o texto completo do vídeo via Whisper e passá-lo para a IA local (Ollama rodando o modelo Qwen).
   - Pedir ao Qwen para identificar o trecho de 30-60 segundos que possui o maior potencial viral (baseado em contexto, ganchos e picos emocionais).
   - O Qwen deve devolver as *timestamps* exatas para o FFmpeg cortar ali, ao invés de fixamente os "primeiros 15 segundos".

3. **Smart Reframe (Rastreamento Facial):**
   - Atualmente, o recorte 9:16 é estático no centro do vídeo (`crop=ih*9/16:ih`).
   - Recomenda-se adicionar a biblioteca `OpenCV` (Python) para ler as coordenadas do rosto de quem está falando quadro a quadro, passando essas coordenadas dinâmicas para o filtro de crop do FFmpeg, mantendo o palestrante sempre focado.

4. **Upload de Arquivos Locais:**
   - O frontend já possui o `<input type="file">`.
   - É necessário criar uma nova rota (`@app.post("/upload")`) no FastAPI para receber `.mp4` via `UploadFile`, salvá-los no disco e rodar o mesmo fluxo do `process_video`.

## 💻 Como Rodar o Projeto

**Para ligar o Back-end:**
```bash
cd backend
pip install fastapi uvicorn yt-dlp pydantic
python main.py
```
*(Rodará em http://0.0.0.0:8000)*

**Para ligar o Front-end:**
```bash
npm install
npm run dev
```
*(Rodará em http://localhost:5174)*
