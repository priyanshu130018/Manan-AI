# Manan AI

A production-ready Retrieval-Augmented Generation (RAG) application that enables users to upload PDF documents, build a searchable knowledge base, and interact with it through an AI-powered chat interface. Manan AI combines semantic search with Google's Gemini models to generate accurate, context-aware responses with source citations.

---

## Table of Contents

- Overview
- Features
- Technology Stack
- Project Structure
- Prerequisites
- Backend Setup
- Frontend Setup
- Connecting Frontend & Backend
- API Endpoints
- License

---

# Overview

Manan AI is designed to answer questions using information from user-uploaded documents rather than relying solely on a large language model.

The application follows a Retrieval-Augmented Generation (RAG) workflow:

- Upload PDF documents
- Extract and chunk document text
- Generate vector embeddings
- Store embeddings in ChromaDB
- Retrieve relevant document chunks for user queries
- Generate AI responses using Google Gemini
- Display source citations with every response

---

# Features

### Document Management

- Upload PDF documents
- Automatic text extraction
- Intelligent document chunking
- View uploaded documents
- Delete indexed documents

### AI Chat

- Chat with uploaded documents
- Semantic similarity search
- Context-aware responses
- Source citations
- Conversation memory
- Query rewriting
- Conversation summarization

### User Interface

- Modern React interface
- Responsive design
- Dark mode support
- Upload progress indicator
- Document management dashboard

---

# Technology Stack

## Backend

- Python
- FastAPI
- Pydantic
- Google Gemini API
- ChromaDB

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Axios
- TanStack Router

---

# Project Structure

```text
Manan/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── ai/
│   │   │   ├── embeddings/
│   │   │   ├── evaluation/
│   │   │   ├── ingestion/
│   │   │   ├── llm/
│   │   │   ├── memory/
│   │   │   ├── pipelines/
│   │   │   ├── prompts/
│   │   │   ├── retrieval/
│   │   │   └── vector_store/
│   │   │
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   ├── documents.py
│   │   │   ├── upload.py
│   │   │   └── routes.py
│   │   │
│   │   ├── core/
│   │   ├── middleware/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   │
│   ├── public/
│   │
│   ├── src/
│   │   │
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── styles/
│   │   ├── types/
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── README.md
└── .gitignore
```

---

# Folder Description

## Backend

| Folder | Description |
|---------|-------------|
| `ai/` | Core RAG implementation including embeddings, retrieval, pipelines, memory, prompts, evaluation, and vector store. |
| `api/` | API route definitions for chat, upload, and document management. |
| `core/` | Application configuration and startup settings. |
| `middleware/` | Middleware such as CORS and request handling. |
| `schemas/` | Pydantic request and response models. |
| `services/` | Business logic used by API routes. |
| `utils/` | Shared helper functions. |

## Frontend

| Folder | Description |
|---------|-------------|
| `components/` | Reusable UI components. |
| `hooks/` | Custom React hooks. |
| `routes/` | Application pages managed by TanStack Router. |
| `services/` | API communication using Axios. |
| `styles/` | Global styling configuration. |
| `types/` | Shared TypeScript interfaces and types. |

---

# Prerequisites

Install the following software before running the project.

- Python 3.11 or later
- Node.js 18 or later
- npm
- Google Gemini API Key

---

# Backend Setup

## 1. Navigate to Backend

```bash
cd backend
```

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create a `.env` file inside the backend directory.

```env
GOOGLE_API_KEY=YOUR_GEMINI_API_KEY
```

## 5. Run the Backend

```bash
uvicorn app.main:app --reload
```

The backend server will start at

```
http://localhost:8000
```

Swagger Documentation

```
http://localhost:8000/docs
```

---

# Frontend Setup

## 1. Navigate to Frontend

```bash
cd frontend
```

## 2. Install Dependencies

```bash
npm install
```

## 3. Start Development Server

```bash
npm run dev
```

The frontend will be available at

```
http://localhost:8080
```

---

# Connecting Frontend & Backend

The frontend communicates with the backend using Axios.

The backend base URL is configured in:

```text
frontend/src/services/axios.ts
```

Default backend URL

```
http://localhost:8000
```

Before starting the frontend, ensure the backend server is running.

---

# API Endpoints

## Chat

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/chat` | Generate AI responses using uploaded documents. |

---

## Upload

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/upload` | Upload and index PDF documents into the vector database. |

---

## Documents

| Method | Endpoint | Description |
|---------|----------|-------------|
| GET | `/documents` | Retrieve all indexed documents. |
| DELETE | `/documents/{document_id}` | Delete an indexed document. |

---

# License

This project is intended for educational, learning, and portfolio purposes.