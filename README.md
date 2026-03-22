# AutoApply 🚀

An intelligent, open-source job application automation system that tailors your resume for each job and applies autonomously based on your preferences.

## Features

- 🔍 **Intelligent Job Scraping** - Automatically finds new jobs from LinkedIn, GitHub Jobs, and Greenhouse
- 🎯 **Smart Fit Scoring** - Uses AI to match jobs with your resume (0-100% fit)
- ✏️ **Resume Tailoring** - Dynamically customizes your resume for each job based on job description
- 📧 **Email Notifications** - Get approval/confirmation/failure emails at every step
- 🤖 **Dual Application Modes**:
  - **Approval Mode**: New job found → Email sent → YOU approve → Applies
  - **Auto-Apply Mode**: New job found → Score checked → Auto-applies if score ≥ threshold
- ⚙️ **Granular Controls** - Per-company settings, resume customization, keyword filters
- 📊 **Dashboard** - Track all applications, view fit scores, see application history

## Tech Stack

### Backend
- **Python 3.11** - FastAPI, SQLAlchemy, Celery
- **PostgreSQL** - Main database
- **Redis** - Caching & task queue
- **Ollama** - Local LLM for job parsing & scoring (completely free)
- **Playwright** - Web automation & form filling
- **Resend** - Email service (3,000/month free)

### Frontend
- **React 18** + Vite
- **Tailwind CSS** - Styling
- **TanStack Query** - Data fetching
- **WebSocket** - Real-time updates

### Infrastructure
- **Docker Compose** - Local development
- **Fly.io** - Free hosting option (~$7/month for database)

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

### Phase 1: Foundation (Week 1) ✓
- [x] Docker setup
- [x] FastAPI + PostgreSQL
- [x] Job scraping (LinkedIn, GitHub Jobs, Greenhouse)
- [ ] Celery job scheduler

### Phase 2: AI & Parsing (Week 2)
- [ ] Ollama integration
- [ ] Job parser (extract title, skills, seniority)
- [ ] Fit scorer (0-100)
- [ ] Resume upload & parsing

### Phase 3: Resume Tailoring (Week 3)
- [ ] Resume rewriter
- [ ] PDF generation (Jinja2 + WeasyPrint)
- [ ] Dashboard: View tailored resumes

### Phase 4: Email & Approvals (Week 4)
- [ ] Resend email service setup
- [ ] JWT approval tokens
- [ ] Email templates (all 5 types)
- [ ] /approve and /skip endpoints

### Phase 5: Auto-Apply Bot (Week 5)
- [ ] Greenhouse form filler
- [ ] Lever form filler
- [ ] Dedup logic (Redis)
- [ ] Application submission & screenshot

### Phase 6: Polish & Deploy (Week 6)
- [ ] Settings page
- [ ] Dashboard refinements
- [ ] WebSocket real-time updates
- [ ] Deploy to Fly.io

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

**Built with ❤️ by the AutoApply community**
