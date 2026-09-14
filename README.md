# Manan AI - ChatGPT Clone & Document Intelligence Platform

**Manan AI** is an enterprise-grade AI chatbot and document intelligence platform built on **LangChain**, featuring authenticated user isolation, explicit multi-provider model routing (**Google Gemini** + **Ollama**), hybrid RAG retrieval, cross-session long-term memory, in-place message editing, response regeneration, and whole-chat sharing.

---

## Key Characteristics & Design Architecture

- **Single Application Architecture**:
  - Unified repository layout (`backend/`, `frontend/`, `docker/`, `.env`, `docker-compose.yml`).
  - Single PostgreSQL database: `manan_ai`.
  - Audited Alembic schema migrations (`001_v2_schema` and `002_chunks_fts`).

- **Canonical Chat Creation & Navigation**:
  - `/` is the clean landing page. No pre-created sessions or empty chat IDs on page load.
  - First message on `/` calls `POST /chat` directly, creating the session, generating a 10-character `chat_id` / `chat_number`, saving user and assistant messages, and returning the response.
  - Frontend immediately navigates to `/chat/<chat_id>` (e.g. `/chat/92A21B5290`).
  - Sidebar dynamically lists saved chats; clicking any chat navigates to `/chat/<chat_id>` and reloads the exact conversation history.

- **Authentication & Security**:
  - Secure signup, login, and logout with JWT in HTTP-only cookies and bcrypt password hashing.
  - Strict resource isolation: users can only see and manage their own sessions, documents, and memories.

- **Explicit Multi-Model Provider Routing**:
  - Centralized `LLMFactory` routes requests explicitly to **Google Gemini** (`gemini-3.6-flash`, `gemini-2.5-pro`, `gemini-3-pro`) or **Ollama** (`llama3.2:3b`).
  - No silent fallback between providers: errors are reported accurately and cleanly.

- **Configurable Embeddings**:
  - Uses `GeminiEmbedding` when configured, or local HuggingFace `SentenceTransformers` (`all-MiniLM-L6-v2`).
  - Re-embedding requirement: changing the embedding model requires re-indexing documents.

- **Advanced Hybrid RAG & Structured Citations**:
  - Document parsing supporting PDF (with OCR), DOCX, PPTX, TXT, CSV, JSON, SQL, and Images.
  - Dense ChromaDB vector search + PostgreSQL Full-Text Search fused using Reciprocal Rank Fusion (RRF).
  - Return structured citations containing filename, page, chunk index, snippet, and retrieval score.

- **Short-Term & Long-Term Memory**:
  - Rolling conversation summarization and sliding context windows.
  - Automatic extraction of personal facts and preferences during conversation.
  - Full user-facing memory management CRUD (`GET /memories`, `POST /memories`, `PATCH /memories/{id}`, `DELETE /memories/{id}`).

- **Interactive Chat Controls**:
  - In-place message editing (`PATCH /messages/{id}`) with thread truncation and regeneration.
  - Response regeneration (`POST /messages/{id}/regenerate`).
  - 10-digit public chat sharing (`GET /chat/{chat_number}`).
  - Ephemeral temporary chat mode (`is_temporary=True`).

---

## Directory & Configuration Structure

```
Manan-AI/
├── README.md
├── docker-compose.yml
├── .gitignore
├── .env
├── backend/
│   ├── alembic/
│   ├── app/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
├── data/
│   ├── chroma/
│   └── documents/
└── docker/
    └── ollama-init.sh
```

- **Configuration File**: Root `.env` (Loaded relative to project root)
- **Data Storage**:
  - Vector Storage: `./data/chroma/`
  - Document Files: `./data/documents/`

---

## Canonical API Endpoints

| Category | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **System** | `GET` | `/health` | Health status and runtime model info |
| **Auth** | `POST` | `/auth/signup` | Register a new user |
| | `POST` | `/auth/login` | Log in and receive HTTP-only JWT cookie |
| | `POST` | `/auth/logout` | Clear auth cookie |
| | `GET` | `/auth/me` | Fetch authenticated user profile |
| **Profile** | `GET` | `/profile` | View profile and preferences |
| | `PATCH` | `/profile` | Update profile information |
| | `POST` | `/profile/change-password` | Update account password |
| **Chat & Messages** | `POST` | `/chat` | Send prompt with optional documents and model override |
| | `GET` | `/chat/{chat_number}` | View public shared chat conversation |
| | `PATCH` | `/messages/{message_id}` | Edit user message and re-run conversation thread |
| | `POST` | `/messages/{message_id}/regenerate` | Regenerate assistant response |
| **Sessions** | `GET` | `/sessions` | List authenticated user sessions |
| | `GET` | `/sessions/{session_id}` | Retrieve session details and message history |
| | `PATCH` | `/sessions/{session_id}` | Rename or modify session |
| | `DELETE` | `/sessions/{session_id}` | Delete session |
| **Memories** | `GET` | `/memories` | List stored long-term memories |
| | `POST` | `/memories` | Manually record a long-term memory fact |
| | `PATCH` | `/memories/{memory_id}` | Update an existing memory |
| | `DELETE` | `/memories/{memory_id}` | Delete a specific memory |
| | `DELETE` | `/memories` | Clear all user memories |
| **Documents** | `GET` | `/doc` | List authenticated user documents |
| | `POST` | `/doc/upload` | Ingest and index document |
| | `GET` | `/doc/storage` | User storage capacity and quota usage |
| | `GET` | `/doc/{document_id}` | Document metadata |
| | `GET` | `/doc/{document_id}/file` | View/download document |
| | `DELETE` | `/doc/{document_id}` | Delete document and remove its chunks |

---

## Setup & Execution

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- PostgreSQL database server
- Google Gemini API Key (optional if using Ollama only)
- [Ollama](https://ollama.ai) (optional if using Gemini only)

### 1. Database Setup
```sql
CREATE DATABASE manan_ai;
```

### 2. Backend Startup
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run Alembic migrations
cd backend
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Startup
```bash
cd frontend
npm install
npm run dev
# Running on http://localhost:5173
```

### 4. Running Automated Tests
```bash
# Run backend test suite from repository root
python -m pytest backend/tests/
```

### 5. Running with Docker Compose
```bash
# From repository root (starts PostgreSQL, Ollama, Backend, Frontend)
docker compose up --build
```
