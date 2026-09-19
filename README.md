# Manan-AI

An authenticated, production-ready AI conversational assistant and intelligent study platform powered by FastAPI, PostgreSQL + pgvector, LangChain, Google Gemini, and Ollama Cloud (running gpt-oss:120b).

---

## Project Description

**Manan-AI** is an advanced retrieval-augmented generation (RAG) platform and conversational AI assistant designed for seamless document analysis, semantic study materials retrieval, and context-grounded AI interaction. Users can upload documents (PDF, DOCX, PPTX, TXT, images with OCR), which are permanently stored in Cloudinary. Dense 384-dimensional vector embeddings (`all-MiniLM-L6-v2`) are generated and stored directly into PostgreSQL with `pgvector` using an HNSW cosine index. Search combines dense vector similarity with PostgreSQL full-text search (FTS) using Reciprocal Rank Fusion (RRF).

---

## Features

- **Authenticated Multi-Turn Chat**: Secure session-based conversations with message editing, branch regeneration, and persistent conversation summaries.
- **Pure PostgreSQL + pgvector Vector Storage**: Native storage of document chunk vectors in PostgreSQL with high-performance HNSW cosine distance indexing (`vector_cosine_ops`), eliminating external vector database dependencies.
- **Hybrid RAG Retrieval**: Dual-pipeline retrieval combining dense vector similarity search (384-dimensional embeddings via `all-MiniLM-L6-v2`) and sparse keyword full-text search (PostgreSQL FTS), fused via Reciprocal Rank Fusion (RRF).
- **Permanent Cloudinary Document Storage**: Uploaded files are stored permanently in Cloudinary with temporary `/tmp` file spooling deleted immediately in `finally` blocks upon completion or failure.
- **Comprehensive Document & OCR Ingestion**: Support for PDF, DOCX, PPTX, TXT, and OCR image parsing with structure-preserving chunking, configurable upload and storage limits, and transactional persistence.
- **Long-Term Memory**: Automatic fact extraction and manual memory management for personalized user context across sessions.
- **Supported LLM Providers & Models**:
  - **Google Gemini**: `gemini-3.6-flash`
  - **Ollama Cloud**: `gpt-oss:120b` (configurable via `OLLAMA_MODEL`)
- **Strict Configuration Enforcement**: Single source of truth configuration via `.env` with fail-fast startup validation and zero silent fallbacks.
- **Enterprise Security**: Argon2/bcrypt password hashing, HTTP-only JWT session cookies, and Google OAuth 2.0 integration with CSRF state protection.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, Pydantic-Settings, Uvicorn
- **Database & Vectors**: PostgreSQL 16+, `pgvector` extension, HNSW Indexing, Alembic migrations, psycopg3
- **Document Storage**: Cloudinary Cloud Storage
- **Document Processing & OCR**: PyPDF, pdf2image, python-docx, python-pptx, Qwen2.5-VL (`Qwen/Qwen2.5-VL-72B-Instruct` via Hugging Face Hosted Inference API), Pillow
- **Frontend**: React 19, TypeScript, Vite, TanStack Router, TailwindCSS, Axios
- **Deployment & Orchestration**: Docker, Docker Compose, Render (Backend), Vercel (Frontend)

---

## Architecture

```text
                                  +-----------------------+
                                  |     React Client      |
                                  +-----------+-----------+
                                              | (HTTP / REST)
                                              v
+-----------------------------------------------------------------------------------------+
|                                    FastAPI Backend                                      |
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
          |  (Permanent File Storage) | | +-------------------+ +-----------------------+ |
          |                           | | | users / sessions  | |    document_chunks    | |
          |                           | | |    / messages     | |(embedding vector(384))| |
          +---------------------------+ | +-------------------+ +-----------------------+ |
                                        +-------------------------------------------------+
                                                       ^                     ^
                                                       |                     |
                                            +----------+----------+ +--------+---------+
                                            |  Google Gemini API  | | Ollama Cloud API |
                                            | (gemini-3.6-flash)  | |  (gpt-oss:120b)  |
                                            +---------------------+ +------------------+
```

---

## Local Docker Setup

### 1. Clone the repository
```bash
git clone https://github.com/priyanshu130018/Manan-AI.git
cd Manan-AI
```

### 2. Configure Environment Variables
Create your `.env` file from the provided template:
```bash
cp .env.example .env
```
Edit `.env` and fill in:
- PostgreSQL credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)
- Google Gemini API key (`GOOGLE_API_KEY`)
- Ollama Cloud API key (`OLLAMA_API_KEY`, `OLLAMA_BASE_URL=https://ollama.com`, `OLLAMA_MODEL=gpt-oss:120b`)
- Cloudinary credentials (`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`)
- Security settings (`JWT_SECRET_KEY`)

### 3. Start Docker Compose (Frontend + Backend + PostgreSQL)
```bash
docker compose up --build -d
```

> **Note**: Docker Compose runs **frontend**, **backend**, and **postgres**. Ollama is accessed directly as an external Cloud API over HTTPS; no Ollama Docker container or local model download is needed.

### 4. Verify Services
- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL**:
  - Inside Docker network: `postgres:5432`
  - Host access (psql / DBeaver / pgAdmin): `localhost:5433` (mapped from container port 5432)

---

## Cloudinary Document Storage

Uploaded documents are stored permanently in **Cloudinary** and indexed into **PostgreSQL + pgvector**:

### Ingestion Lifecycle:
1. **Upload Request**: Client sends file to `POST /doc/upload`.
2. **Temporary Spool**: File is temporarily buffered into the system `/tmp` directory.
3. **Cloudinary Permanent Upload**: File is securely uploaded to Cloudinary under:
   ```text
   manan-ai/users/{user_id}/documents/{document_id}
   ```
4. **Text Extraction & Chunking**: Content is parsed and split into structure-preserving chunks.
5. **Dense Vector Embeddings**: 384-dimensional embeddings (`all-MiniLM-L6-v2`) are computed and stored in `document_chunks` table in PostgreSQL.
6. **Automatic Cleanup**: The temporary `/tmp` file is deleted in a `finally` block regardless of whether ingestion succeeded or failed.
7. **Failure Rollback**: If parsing or database indexing fails, the uploaded Cloudinary asset is automatically destroyed.

> **Security Note**: The database (`user_id` and `document_id`) is the sole source of truth for authorization. File access via `GET /doc/{document_id}/file` validates the user's authentication before issuing a secure temporary 307 redirect.

---

## OCR Pipeline (Qwen2.5-VL via Hugging Face Hosted Inference API)

- **OCR Service**: Hugging Face Hosted Inference API
- **Model**: `Qwen/Qwen2.5-VL-72B-Instruct`
- **Execution**: Remote HTTPS API (`https://router.huggingface.co/v1/chat/completions`)
- **Local OCR Model**: None (zero local model weights or local torch execution for OCR)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Embedding Dimension**: `384`

### Document OCR Pipeline:
```text
Scanned PDF
    ↓
pdf2image
    ↓
Qwen2.5-VL via Hugging Face (HTTPS API)
    ↓
text
    ↓
chunking (StructurePreservingSplitter)
    ↓
MiniLM embeddings (384d)
    ↓
PostgreSQL + pgvector (HNSW cosine index)
```

- **Zero Local Model Weight Overhead**: Model weights are NOT downloaded or executed inside Docker. Inference is hosted remotely by Hugging Face over HTTPS (`HF_API_TOKEN`).
- **Smart Selective OCR**: Native digital PDFs are parsed directly with `pypdf`. The Hugging Face OCR API is invoked only when extractable text is insufficient (< 40 characters on scanned pages or embedded document images).
- **Structured Markdown Normalization**: OCR output is cleaned and structured into Markdown (preserving tables, headings, LaTeX formulas, and lists) before entering the chunking pipeline.
- **Lightweight Backend Container**: Docker images remain lean and lightweight with no heavy vision-language model footprint.

---

## Ollama Cloud LLM Configuration

Ollama is used as an external cloud API provider over HTTPS:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.6-flash

# Ollama Cloud API Settings
OLLAMA_API_KEY=your_ollama_cloud_api_key_here
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b
```

### Key Guidelines:
- **No Local Server / Container**: No Ollama container or local server (`localhost:11434`) is required.
- **No Model Download**: Models are not downloaded locally; inference runs directly via Ollama Cloud.
- **No GPU Required**: The backend container does not require a GPU for Ollama inference.
- **Security**: `OLLAMA_API_KEY` is a backend-only secret and must never be committed to Git or exposed to the frontend.

### Ollama Cloud Troubleshooting:
- `401 Unauthorized / Authentication failed`: Verify that `OLLAMA_API_KEY` is set correctly in `.env`.
- `429 Rate Limit`: Ollama Cloud rate limit reached; wait before retrying.
- `Connection Error`: Ensure network connectivity to `https://ollama.com`.

---

## Render & Production Deployment

For deploying the backend on Render:
1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables**:
   - `DATABASE_URL`: PostgreSQL with pgvector connection string
   - `GOOGLE_API_KEY`: Google Gemini API key
   - `OLLAMA_API_KEY`: Ollama Cloud API key
   - `OLLAMA_BASE_URL`: `https://ollama.com`
   - `OLLAMA_MODEL`: `gpt-oss:120b`
   - `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`
   - `JWT_SECRET_KEY`, `JWT_ALGORITHM`
   - `FRONTEND_URL`, `GOOGLE_REDIRECT_URI`

---

## Docker Troubleshooting

| Action | Command | Description |
| :--- | :--- | :--- |
| **View Backend Logs** | `docker compose logs -f backend` | Stream real-time logs from FastAPI backend container |
| **View Frontend Logs** | `docker compose logs -f frontend` | Stream logs from Frontend container |
| **View Postgres Logs** | `docker compose logs -f postgres` | Stream real-time logs from PostgreSQL pgvector container |
| **Check Container Status** | `docker compose ps` | View running containers and port mappings |
| **Stop Containers** | `docker compose down` | Stop containers while preserving database volume |
| **Reset Database** | `docker compose down -v` | Stop containers and delete named PostgreSQL volume |
| **Rebuild Containers** | `docker compose up --build -d` | Rebuild images and start services |

---

## Testing

Run the automated test suite with `pytest`:

```bash
cd backend
pytest -v
```

Build the frontend for production:

```bash
cd frontend
npm run build
```

---

## Author

Author: **priyanshu130018** (Priyanshu Verma)
