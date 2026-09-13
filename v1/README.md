# Manan AI - V1 (Simple Anonymous Gemini Chatbot)

V1 is a lightweight, zero-friction AI chatbot powered directly by Google Gemini with optional document intelligence (RAG).

## Characteristics
- **Anonymous**: No login, no signup, no user profile, no cookies tracking identity.
- **Gemini-Only**: Clean direct Gemini API integration (no Ollama, no LangChain dependencies).
- **Optional Document RAG**: Upload documents and chat against them with citations.
- **Temporary Chat**: Session-less ephemeral conversations.
- **Shareable URLs**: 10-digit public `chat_number` (`/v1/chat/<10-digit-id>`).
- **Database**: PostgreSQL `manan_ai_v1` using its own independent Alembic migrations.

## Endpoints (`/v1`)
- `GET /v1/health`
- `POST /v1/chat`
- `GET /v1/sessions`
- `POST /v1/sessions`
- `GET /v1/sessions/by-number/{chat_number}`
- `GET /v1/sessions/{session_id}`
- `PATCH /v1/sessions/{session_id}`
- `DELETE /v1/sessions/{session_id}`
- `GET /v1/documents`
- `POST /v1/documents/upload`
- `GET /v1/documents/storage`
- `GET /v1/documents/{document_id}`
- `GET /v1/documents/{document_id}/file`
- `DELETE /v1/documents/{document_id}`

## Setup & Running

```bash
# 1. Database
# CREATE DATABASE manan_ai_v1;

# 2. Backend
cd backend
cp .env.example .env
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001

# 3. Frontend
cd ../frontend
npm install
npm run dev # runs on http://localhost:5173/v1
```

## Testing
```bash
cd backend
python -m pytest tests -v
```
