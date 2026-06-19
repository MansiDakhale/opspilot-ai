#  OpsPilot AI

> **An AI-powered operations assistant** that combines RAG (Retrieval-Augmented Generation), multi-agent orchestration, and an intuitive chat interface to help teams automate and accelerate DevOps workflows.

 **Live Demo:** [http://opspilot-ai-frontend.s3-website.ap-south-1.amazonaws.com/](http://opspilot-ai-frontend.s3-website.ap-south-1.amazonaws.com/)

---

##  Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development (Docker)](#local-development-docker)
  - [Frontend Only](#frontend-only)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

##  Overview

OpsPilot AI is a full-stack intelligent assistant built for engineering and operations teams. It leverages a **LangGraph-based multi-agent pipeline** to handle complex queries, generate reports, write scripts, retrieve context from uploaded documents, and maintain conversational memory — all from a single chat interface.

---

##  Features

| Feature | Description |
|---|---|
|  **AI Chat** | Real-time chat powered by LLM with streaming support |
|  **Memory Agent** | Remembers user preferences and past interactions |
|  **RAG Pipeline** | Upload PDFs/docs and query them with semantic search (ChromaDB + HuggingFace Embeddings) |
|  **Planner Agent** | Breaks complex tasks into structured step-by-step plans |
|  **Coder Agent** | Generates shell scripts, Python code, and automation snippets |
|  **Reporting Agent** | Produces downloadable reports from conversations |
|  **Retrieval Agent** | Fetches relevant context from the knowledge base |
|  **Chat History** | Persistent conversation sessions per user |
|  **Auth** | JWT-based user authentication (register / login) |
|  **Async Workers** | Celery + Redis for background task processing |

---

##  Tech Stack

### Frontend
- **React 19** + **Vite 8**
- **Tailwind CSS 3**
- **React Markdown** + **Syntax Highlighter**
- Deployed on **AWS S3** (static hosting)

### Backend
- **FastAPI** — REST API framework
- **LangChain** + **LangGraph** — Multi-agent orchestration
- **Ollama** — Local LLM inference
- **ChromaDB** — Vector store for RAG
- **HuggingFace Sentence Transformers** — Embeddings
- **PostgreSQL** (pgvector) — Relational DB + vector extension
- **Redis** + **Celery** — Async task queue
- **PyMuPDF / Tesseract** — PDF and OCR processing
- Deployed on **AWS EC2** (Docker)

---

##  Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│          (AWS S3 Static Hosting — Vite Build)            │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API / HTTP
┌───────────────────────▼─────────────────────────────────┐
│                  FastAPI Backend (EC2)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │   Auth   │  │   Chat   │  │   RAG    │  │ Agents │  │
│  └──────────┘  └──────────┘  └──────────┘  └───┬────┘  │
│                                                 │        │
│  ┌──────────────────────────────────────────────▼─────┐ │
│  │          LangGraph Multi-Agent Workflow             │ │
│  │  Planner → Coder → Memory → Retrieval → Reporter   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  PostgreSQL  │  │   ChromaDB   │  │  Redis/Celery │  │
│  │  (pgvector)  │  │ (Vector RAG) │  │ (Async Tasks) │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└───────────────────────────────────────────────────────────┘
```

---

##  Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- [Node.js 18+](https://nodejs.org/) (for frontend-only dev)
- [Ollama](https://ollama.com/) running locally with a model pulled (e.g. `ollama pull llama3`)

### Local Development (Docker)

Clone the repository and spin up all services with a single command:

```bash
git clone https://github.com/MansiDakhale/opspilot-ai.git
cd opspilot-ai

# Copy and configure environment variables
cp backend/.env.example backend/.env   # edit with your values

# Start all services (backend, postgres, redis, worker)
docker-compose up --build
```

The API will be available at: `http://localhost:8000`

> **Health check:** `GET http://localhost:8000/` → `{"status": "OpsPilot AI Engine is Online"}`

### Frontend Only

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at: `http://localhost:5173`

---

##  Environment Variables

Create a `backend/.env` file with the following keys:

```env
# Database
DATABASE_URL=postgresql://opspilot:opspilot@postgres:5432/opspilot_db

# Redis / Celery
REDIS_URL=redis://redis:6379/0

# JWT Auth
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Ollama (LLM)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3

# HuggingFace Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

##  Project Structure

```
opspilot-ai/
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx    # Main chat interface
│   │   │   ├── LoginPage.jsx   # Authentication
│   │   │   └── SignupPage.jsx  # Registration
│   │   ├── components/         # Reusable UI components
│   │   ├── context/            # React context (auth, etc.)
│   │   └── App.jsx
│   └── package.json
│
├── backend/                    # FastAPI backend
│   └── app/
│       ├── api/                # Route handlers
│       │   ├── auth.py         # JWT login / register
│       │   ├── chat.py         # AI chat endpoint
│       │   ├── rag.py          # Document upload & query
│       │   ├── agents.py       # Agent invocation
│       │   └── chat_history.py # Session history
│       ├── agents/             # LangGraph agent pipeline
│       │   ├── workflow.py     # Graph orchestration
│       │   ├── planner_agent.py
│       │   ├── coder_agent.py
│       │   ├── memory_agent.py
│       │   ├── reporting_agent.py
│       │   ├── retrieval_agent.py
│       │   └── summarizer_agent.py
│       ├── models/             # SQLAlchemy DB models
│       ├── schemas/            # Pydantic schemas
│       ├── services/           # Business logic
│       ├── workers/            # Celery async tasks
│       ├── db/                 # Database connection
│       └── main.py             # App entry point
│
├── docker-compose.yml          # Local dev stack
├── docker-compose.prod.yml     # Production stack
└── README.md
```

---

##  API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Login & receive JWT token |
| `POST` | `/ai/chat` | Send a message to the AI |
| `POST` | `/rag/upload` | Upload a document for RAG |
| `POST` | `/rag/query` | Query the knowledge base |
| `POST` | `/agents/run` | Run the full multi-agent pipeline |
| `GET` | `/history/sessions` | Get all chat sessions |
| `GET` | `/history/messages/{session_id}` | Get messages for a session |
| `GET` | `/reports/{filename}` | Download a generated report |

---

##  Deployment

### Frontend → AWS S3
The frontend is built with Vite and deployed to an S3 bucket configured for static website hosting.

```bash
cd frontend
npm run build
# Upload the dist/ folder to your S3 bucket
aws s3 sync dist/ s3://opspilot-ai-frontend --delete
```

### Backend → AWS EC2 (Docker)
The backend and workers run as Docker containers on an EC2 instance.

```bash
# On your EC2 instance
git pull origin main
docker-compose -f docker-compose.prod.yml up --build -d
```

---

##  Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

##  License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">
  <strong>Built by the OpsPilot AI team</strong>
</div>
