# Manan-AI

An authenticated, production-ready AI conversational assistant and intelligent study platform powered by FastAPI, PostgreSQL + pgvector, LangChain, Google Gemini, and Alibaba Cloud Qwen.

---

## Project Description

**Manan-AI** is an advanced retrieval-augmented generation (RAG) platform and conversational AI assistant designed for seamless document analysis, semantic study materials retrieval, and context-grounded AI interaction. It allows users to upload documents (PDF, DOCX, PPTX, TXT, images with OCR), stores assets securely on Cloudinary, generates dense vector embeddings, indexes them directly into PostgreSQL with `pgvector` using an HNSW index, and combines vector similarity search with full-text keyword search using Reciprocal Rank Fusion (RRF).

---

## Features

- **Authenticated Multi-Turn Chat**: Secure session-based conversations with message editing, branch regeneration, and persistent conversation summaries.
- **Pure PostgreSQL + pgvector Vector Storage**: Native storage of document chunk vectors in PostgreSQL with high-performance HNSW cosine distance indexing (`vector_cosine_ops`), eliminating external vector database dependencies.
- **Hybrid RAG Retrieval**: Dual-pipeline retrieval combining dense vector similarity search (384-dimensional embeddings via `all-MiniLM-L6-v2`) and sparse keyword full-text search (PostgreSQL FTS), fused via Reciprocal Rank Fusion (RRF).
- **Cloud Document Storage**: Secure storage and asset management via Cloudinary with temporary file spooling and cleanup on upload, plus secure authenticated redirects for document delivery.
- **Comprehensive Ingestion & OCR**: Support for PDF, DOCX, PPTX, TXT, and OCR image parsing with structure-preserving chunking, configurable upload and storage limits, and transactional persistence.
- **Long-Term Memory**: Automatic fact extraction and manual memory management for personalized user context across sessions.
- **Production LLM Models**: Multi-model routing supporting Google Gemini (`gemini-3.6-flash`) and Alibaba Cloud Model Studio Qwen (`qwen3.8-27b`).
- **Strict Configuration Enforcement**: Single source of truth configuration via `.env` with fail-fast startup validation and zero silent fallbacks.
- **Enterprise Security**: Argon2/bcrypt password hashing, HTTP-only JWT session cookies, and Google OAuth 2.0 integration with CSRF state protection.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn
- **Database & Vectors**: PostgreSQL 16+, `pgvector` extension, HNSW Indexing, Alembic migrations, psycopg3
- **Document Storage**: Cloudinary Cloud Storage
- **AI & RAG**: LangChain, Google Gemini API (`google-genai`), Alibaba Cloud Model Studio Qwen API, Sentence-Transformers / FastEmbed (`all-MiniLM-L6-v2`)
- **Document Processing**: PyPDF, python-docx, python-pptx, PyTesseract (OCR), Pillow
- **Frontend**: React 19, TypeScript, Vite, TanStack Router, TailwindCSS, Axios
- **Deployment**: Render (Backend Docker Web Service + PostgreSQL with pgvector), Vercel (Frontend Single Page Application)

---

## Architecture

```text
                                  +-----------------------+
                                  |  React Client (Vercel)|
                                  +-----------+-----------+
                                              | (HTTP / REST)
                                              v
+-----------------------------------------------------------------------------------------+
|                              FastAPI Backend (Render)                                   |
|                                                                                         |
|  +-------------------+    +---------------------+    +-------------------------------+  |
|  |   Auth Service    |    |  Document Service   |    |         Chat Service          |  |
|  +-------------------+    +----------+----------+    +---------------+---------------+  |
|                                      |                               |                  |
|                                      v                               v                  |
|                        +---------------------------+   +-----------------------------+  |
|                        | Document Ingestion & OCR  |   |    RAG Hybrid Retrieval     |  |
|                        | (Splitter + Embeddings)   |   |   (Dense + Sparse + RRF)    |  |
|                        +-------------+-------------+   +--------------+--------------+  |
|                                      |                                |                 |
+--------------------------------------|--------------------------------|-----------------+
                                       |                                |
                        +--------------+--------------+                 |
                        |                             |                 |
                        v                             v                 v
          +---------------------------+ +-------------------------------------------------+
          |    Cloudinary Storage     | |           PostgreSQL with pgvector              |
          |  (Secure Asset Delivery)  | | +-------------------+ +-----------------------+ |
          +---------------------------+ | | users / sessions  | |    document_chunks    | |
                                        | |    / messages     | |(embedding vector(384))| |
                                        | +-------------------+ +-----------------------+ |
                                        +-------------------------------------------------+
                                                       ^                     ^
                                                       |                     |
                                            +----------+----------+ +--------+---------+
                                            |  Google Gemini API  | |  Alibaba Qwen    |
                                            | (gemini-3.6-flash)  | |  (qwen3.8-27b)   |
                                            +---------------------+ +------------------+
```

---

## Project Structure

```text
Manan-AI/
├── .env.example                 # Documented template of required environment variables
├── .env                         # Single source of truth environment configuration
├── docker-compose.yml           # Multi-container orchestration (PostgreSQL+pgvector, Backend, Frontend)
├── Dockerfile                   # Production container build for FastAPI backend (Render ready)
├── README.md                    # Project documentation
├── backend/
│   ├── alembic/                 # Database migrations
│   │   ├── versions/            # Versioned migration scripts (001 through 004_cloudinary_storage)
│   │   └── env.py               # Alembic configuration connected to application settings
│   ├── alembic.ini              # Alembic environment definitions
│   ├── requirements.txt         # Backend Python dependencies
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, middleware, and exception handlers
│   │   ├── api/                 # API Layer
│   │   │   ├── dependencies/    # Dependency injection (Auth, Services, Repositories)
│   │   │   ├── middleware/      # CORS and security middleware
│   │   │   └── routes/          # Standardized API routes (auth, chat, documents, memories, models, profile, sessions)
│   │   ├── core/                # Core configuration, exceptions, and logging
│   │   ├── integrations/        # External integrations (Gemini, Qwen, Embeddings, Parsers, Storage)
│   │   │   ├── gemini/          # Google Gemini integration
│   │   │   ├── qwen/            # Alibaba Cloud Model Studio Qwen integration
│   │   │   ├── storage/         # Cloudinary cloud storage
│   │   │   ├── embeddings/      # Dense vector embeddings
│   │   │   └── parsers/         # Multi-format document & OCR parsers
│   │   ├── models/              # SQLAlchemy / psycopg models, entities, and Pydantic schemas
│   │   ├── repositories/        # Database access layer (PostgreSQL pgvector VectorRepository, DocumentRepository, etc.)
│   │   ├── services/            # Business logic (Auth, Chat, Document, Memory, RAG, Retrieval)
│   │   └── utils/               # Text normalization and helper utilities
│   └── tests/                   # Test suite (config, pgvector retrieval, API contracts, Qwen, Cloudinary)
└── frontend/                    # React + TypeScript + Vite frontend application (Vercel ready)
    ├── src/
    │   ├── components/          # UI components (Chat, Documents, Navigation, Modals)
    │   ├── routes/              # TanStack router page views
    │   ├── services/            # Typed API client services
    │   └── types/               # Shared TypeScript schemas
    ├── vercel.json              # Vercel SPA routing configuration
    └── package.json             # Frontend dependencies and scripts
```

---

## Environment Variables

All configuration is strictly validated on application startup. If any mandatory variable is missing, startup fails immediately with a descriptive error.

| Variable | Description | Example |
| :--- | :--- | :--- |
| `APP_NAME` | Name of the application | `Manan AI` |
| `ENV` | Environment mode (`development` / `production` / `test`) | `production` |
| `HOST` | Backend bind host | `0.0.0.0` |
| `PORT` | Backend bind port | `8000` |
| `DATABASE_URL` | PostgreSQL connection string with pgvector | `postgresql://postgres:password@host:5432/manan_ai` |
| `JWT_SECRET_KEY` | Secret key for signing JWT tokens | `your-32-char-random-secret-key` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan in minutes | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifespan in days | `7` |
| `SESSION_EXPIRY_DAYS` | Session expiry lifespan in days | `30` |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `GOOGLE_CLIENT_ID` | (Optional) Google OAuth 2.0 client ID | `...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | (Optional) Google OAuth 2.0 client secret | `GOCSPX-...` |
| `GOOGLE_REDIRECT_URI` | Google OAuth redirect callback URL | `https://your-backend.onrender.com/auth/google/callback` |
| `FRONTEND_URL` | Base URL for frontend application | `https://your-frontend.vercel.app` |
| `LLM_PROVIDER` | Default LLM provider (`gemini` or `qwen`) | `gemini` |
| `LLM_MODEL` | Default LLM model name | `gemini-3.6-flash` |
| `QWEN_API_KEY` | Alibaba Cloud Model Studio API key | `sk-...` |
| `QWEN_BASE_URL` | Alibaba Cloud Model Studio Base URL | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODEL` | Qwen model identifier | `qwen3.8-27b` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Cloud Name | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API Key | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Cloudinary API Secret | `your-cloudinary-secret` |
| `CLOUDINARY_FOLDER` | Cloudinary folder prefix | `manan-ai` |
| `EMBEDDING_PROVIDER` | Embedding provider (`fastembed` or `local`) | `fastembed` |
| `EMBEDDING_MODEL` | Embedding model identifier | `sentence-transformers/all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Dimension of embedding vectors | `384` |
| `UPLOAD_DIR` | Directory for temporary upload spooling | `./data/documents` |
| `MAX_UPLOAD_SIZE_MB` | Maximum single document upload size (MB) | `50` |
| `TOTAL_STORAGE_LIMIT_MB` | Maximum total user storage quota (MB) | `500` |
| `CHUNK_SIZE` | Text chunk size in characters | `500` |
| `CHUNK_OVERLAP` | Overlap between consecutive chunks | `50` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `https://your-frontend.vercel.app,http://localhost:5173` |
| `VITE_API_BASE_URL` | Frontend API backend URL | `https://your-backend.onrender.com` |

---

## Production Deployment Guide

### 1. Database Setup on Render (PostgreSQL with pgvector)
1. In Render Dashboard, create a **New PostgreSQL Database**.
2. Set PostgreSQL Version to **16**.
3. In database connection or psql shell, verify the `vector` extension is enabled:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Copy the **Internal Database URL** (or External for initial migrations).

### 2. Cloudinary Setup (Document Storage)
1. Sign up or log into [Cloudinary](https://cloudinary.com/).
2. From your Cloudinary Dashboard, obtain:
   - **Cloud Name** (`CLOUDINARY_CLOUD_NAME`)
   - **API Key** (`CLOUDINARY_API_KEY`)
   - **API Secret** (`CLOUDINARY_API_SECRET`)

### 3. Backend Deployment on Render (FastAPI Docker Service)
1. Create a **New Web Service** connected to your repository on Render.
2. Select **Docker** environment.
3. Configure Environment Variables in Render:
   - `DATABASE_URL`: Your Render PostgreSQL connection string
   - `GOOGLE_API_KEY`: Your Google Gemini API Key
   - `QWEN_API_KEY`: Your Alibaba Cloud Model Studio API Key
   - `QWEN_BASE_URL`: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
   - `QWEN_MODEL`: `qwen3.8-27b`
   - `CLOUDINARY_CLOUD_NAME`: Your Cloudinary cloud name
   - `CLOUDINARY_API_KEY`: Your Cloudinary API key
   - `CLOUDINARY_API_SECRET`: Your Cloudinary API secret
   - `CLOUDINARY_FOLDER`: `manan-ai`
   - `JWT_SECRET_KEY`: High-entropy random 32+ character string
   - `FRONTEND_URL`: `https://<your-vercel-app>.vercel.app`
   - `CORS_ALLOWED_ORIGINS`: `https://<your-vercel-app>.vercel.app`
   - `ENV`: `production`
4. Render automatically executes the Dockerfile `CMD`, running `alembic upgrade head` followed by Uvicorn on `${PORT}`.

### 4. Frontend Deployment on Vercel
1. In Vercel Dashboard, import the Git repository.
2. Set **Root Directory** to `frontend`.
3. Framework Preset: **Vite**.
4. Configure Environment Variables:
   - `VITE_API_BASE_URL`: `https://<your-render-service>.onrender.com`
5. Deploy! Vercel uses `frontend/vercel.json` for client-side SPA routing rewrites.

---

## Local Development

```bash
# 1. Setup Backend
cd backend
python -m venv .venv
.venv\Scripts\activate   # On Windows (or 'source .venv/bin/activate' on Linux/macOS)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Setup Frontend (in separate terminal)
cd frontend
npm install
npm run dev
```

---

## Running with Docker Compose

```bash
docker compose up --build
```

---

## API Documentation

All API responses follow the standardized `ApiResponse[T]` format:
```json
{
  "success": true,
  "message": "Human readable summary",
  "data": { ... }
}
```

### Core API Groups

| Group | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Health** | `GET` | `/health` | Application status and model provider info |
| **Auth** | `POST` | `/auth/signup` | Register new user and set session cookie |
| | `POST` | `/auth/login` | Authenticate user credentials |
| | `POST` | `/auth/logout` | Clear session cookie |
| | `GET` | `/auth/me` | Fetch authenticated user profile |
| | `GET` | `/auth/google/login` | Initiate Google OAuth 2.0 flow |
| | `GET` | `/auth/google/callback` | OAuth redirect callback handler |
| **Chat** | `POST` | `/chat` | Send message, perform hybrid RAG retrieval, generate answer |
| | `GET` | `/chat/{chat_number}` | Retrieve public shared chat by 10-digit number |
| **Messages** | `PATCH` | `/messages/{message_id}` | Edit user message and regenerate response turn |
| | `POST` | `/messages/{message_id}/regenerate` | Regenerate assistant response |
| **Sessions** | `GET` | `/sessions` | List active user chat sessions |
| | `POST` | `/sessions` | Create new session |
| | `GET` | `/sessions/{session_id}` | Get session details and full message history |
| | `PATCH` | `/sessions/{session_id}` | Update session title or active document filters |
| | `DELETE` | `/sessions/{session_id}` | Delete session and its messages |
| **Documents** | `POST` | `/doc/upload` | Upload to Cloudinary, parse, chunk, and index in pgvector |
| | `GET` | `/doc` | List all user documents and processing statuses |
| | `GET` | `/doc/storage` | Get storage quota and usage breakdown |
| | `GET` | `/doc/{document_id}` | Get document metadata and chunk stats |
| | `GET` | `/doc/{document_id}/file` | Secure redirect (307) to Cloudinary asset |
| | `DELETE` | `/doc/{document_id}` | Delete document, Cloudinary asset, and pgvector embeddings |
| **Memories** | `GET` | `/memories` | List long-term memory facts |
| | `POST` | `/memories` | Add manual memory fact |
| | `PATCH` | `/memories/{memory_id}` | Update memory content |
| | `DELETE` | `/memories/{memory_id}` | Delete single memory |
| | `DELETE` | `/memories` | Clear all user memories |
| **Models** | `GET` | `/llm/models` | List available Gemini & Qwen models |

---

## Testing

Run the automated test suite using `pytest`:

```bash
cd backend
pytest tests/ -v
```

---

## Author

Author: **priyanshu130018** (Priyanshu Verma)
