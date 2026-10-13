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
- Resume Version Comparison
- Adaptive Interview Practice

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
- Tailwind CSS
- React Query
- Framer Motion

### AI

- Groq
- Llama 3.1

## Local Development

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend (requires Redis running on localhost:6379)
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access the application at http://localhost
```

### Individual Container Builds

**Backend:**
```bash
# Build backend image
docker build -f backend.Dockerfile -t resumeiq-backend:latest .

# Run backend (requires Redis)
docker run -p 8000:8000 \
  -e REDIS_HOST=redis \
  -e REDIS_PORT=6379 \
  --link redis:redis \
  resumeiq-backend:latest
```

**Frontend:**
```bash
# Build frontend image
docker build -f frontend.Dockerfile -t resumeiq-frontend:latest .

# Run frontend
docker run -p 80:80 resumeiq-frontend:latest
```

### Docker Hub Push

```bash
# Tag images
docker tag resumeiq-backend:latest your-dockerhub-username/resumeiq-backend:latest
docker tag resumeiq-frontend:latest your-dockerhub-username/resumeiq-frontend:latest

# Push to Docker Hub
docker push your-dockerhub-username/resumeiq-backend:latest
docker push your-dockerhub-username/resumeiq-frontend:latest
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `GROQ_API_KEY` (optional - system works offline)
- `REDIS_HOST` (default: localhost)
- `REDIS_PORT` (default: 6379)
- `CORS_ORIGINS` (default: http://localhost:5173)

### Docker Compose Services

- **redis**: Redis 7 Alpine with persistent volume
- **backend**: FastAPI with health checks and database persistence
- **frontend**: Nginx serving React build

### Volumes

- `redis_data`: Redis persistence
- `./resumeiq.db`: SQLite database (mounted from host)