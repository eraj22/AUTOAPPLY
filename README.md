# AutoApply 🚀

An intelligent, open-source job application automation system that tailors your resume for each job and applies autonomously based on your preferences.

## Phase 1: Foundation Complete ✅

This is the Phase 1 release featuring the core development infrastructure and API foundation.

### What's Included

- ✅ **Docker Development Environment** - Complete docker-compose setup with PostgreSQL, Redis, and Ollama
- ✅ **FastAPI Backend** - RESTful API with 14 CRUD endpoints for companies, jobs, and settings
- ✅ **React Dashboard** - Modern frontend with Vite, Tailwind CSS, and real-time data fetching
- ✅ **Database Models** - 7 SQLAlchemy tables with full schema for job tracking and resume management
- ✅ **API Documentation** - Interactive Swagger UI at `/docs`
- ✅ **Environment Configuration** - Ready-to-use setup with `.env` template
- ✅ **Production-Ready Structure** - Organized backend services, frontend components, and infrastructure files

## Tech Stack

### Backend
- **Python 3.11** - FastAPI, SQLAlchemy, Pydantic
- **PostgreSQL 15** - Main database
- **Redis 7** - Caching & task queue
- **Ollama** - Local LLM (installed, ready for Phase 2)
- **Docker** - Container orchestration

### Frontend
- **React 18** + Vite
- **Tailwind CSS** - Utility-first styling
- **TanStack Query** - Data fetching & caching
- **Axios** - HTTP client

### Infrastructure
- **Docker Compose** - Full local development environment
- **Alpine Linux** - Minimal, secure base images

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/autoapply.git
cd autoapply

# Copy environment template
cp .env.example .env
```

### 2. Start Services with Docker Compose

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Ollama (port 11434)
- FastAPI Backend (port 8000)
- React Frontend (port 5173)

### 3. Initialize Ollama Model

```bash
docker exec autoapply-ollama ollama pull mistral
```

### 4. Access the App

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Project Structure

```
autoapply/
├── backend/
│   ├── app/
│   │   ├── models.py             # Database tables
│   │   ├── schemas.py            # API request/response schemas
│   │   ├── config.py             # Settings & environment
│   │   ├── database.py           # DB connection
│   │   ├── api/
│   │   │   ├── companies.py      # Company CRUD
│   │   │   ├── jobs.py           # Job endpoints
│   │   │   ├── resume.py         # Resume management
│   │   │   └── applications.py   # Application history
│   │   └── services/
│   │       ├── scraper.py        # Playwright scraping
│   │       ├── llm_parser.py     # Ollama LLM integration
│   │       ├── fit_scorer.py     # Job matching logic
│   │       └── email_service.py  # Email notifications
│   ├── tasks/                    # Celery background tasks
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/           # React components
│   │   ├── pages/                # Page components
│   │   ├── api/                  # API client
│   │   └── App.jsx
│   └── package.json
│
└── docker-compose.yml
```

## Build Phases

### Phase 1: Foundation ✅ (CURRENT RELEASE)
- [x] Docker setup (PostgreSQL, Redis, Ollama, Backend, Frontend)
- [x] FastAPI backend with database integration
- [x] React frontend with dashboard
- [x] SQLAlchemy ORM with 7 database tables
- [x] API endpoints (14 CRUD operations)
- [x] Environment configuration & Docker networking
- [x] GitHub repository & MIT License

### Phase 2: Job Scraper ⏳
- [ ] Playwright-based job board scraping
- [ ] LinkedIn, Indeed, Glassdoor integration
- [ ] Job parsing & normalization
- [ ] Duplicate detection & filtering

### Phase 3: Application Bot ⏳
- [ ] Ollama LLM integration for AI parsing
- [ ] Resume matching & scoring
- [ ] Auto-application workflow
- [ ] Form filling & submission

### Phase 4: Email Notifications ✅ (April 2026)
- [x] Resend API integration
- [x] 5 professional HTML email templates
- [x] Email logging & tracking database
- [x] JWT approval/skip action links
- [x] Async email service with error handling

### Phase 5: Workflow Integration ⏳
- [ ] Phase 1-3 pipeline orchestration
- [ ] Job matching triggers
- [ ] Approval workflow
- [ ] Error handling & retries

### Phase 6: Settings Dashboard ✅ (April 2026)
- [x] User settings configuration API
- [x] Approval vs auto-apply modes
- [x] Job fit score thresholds
- [x] Application keywords & preferences
- [x] React UI with form controls

See [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) for detailed Phase 1 documentation.

## Local Development

### Backend Only

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Start Postgres & Redis separately or via Docker
docker-compose up postgres redis

# Run server
uvicorn app.main:app --reload
```

### Frontend Only

```bash
cd frontend
npm install
npm run dev
```

## API Documentation

Once running, visit http://localhost:8000/docs for interactive Swagger UI documentation.

## Environment Variables

See `.env.example` for all available variables. Key ones:

- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `OLLAMA_API_URL` - Ollama endpoint
- `RESEND_API_KEY` - Email service key
- `JWT_SECRET_KEY` - Token signing key

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details

## Support

- 📖 [Documentation](./docs) (coming soon)
- 🐛 [Report a bug](https://github.com/yourusername/autoapply/issues)
- 💡 [Request a feature](https://github.com/yourusername/autoapply/discussions)

## Disclaimer

This tool is designed to automate job applications. Users are responsible for ensuring their use complies with job board Terms of Service and applicable laws. We are not liable for any consequences resulting from improper use.

---

**Built with ❤️ by the eraz**

