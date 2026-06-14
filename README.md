# AI Resume Analyzer

AI-powered Resume Analyzer built using:

- FastAPI
- Groq LLM
- Redis
- React
- Vite
- NLP
- PyMuPDF

## Features

- Resume PDF Upload
- ATS Score Analysis
- Strength & Weakness Detection
- Missing Skills Identification
- AI Suggestions
- Redis Caching
- Interview Question Generator

## Tech Stack

### Backend

- FastAPI
- Python
- Redis
- PyMuPDF
- NLTK
- HTTPX

### Frontend

- React
- Vite
- Axios
- Tailwind CSS

### AI

- Groq
- Llama 3.1

## Run Backend

```bash
pip install -r requirements.txt

uvicorn app.main:app --reload