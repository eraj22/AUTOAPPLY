#!/bin/bash
# Seed test jobs into the database for Phase 3A demo

echo "🌱 Seeding test jobs..."

docker exec -i autoapply-postgres psql -U autoapply -d autoapply_db <<'ENDSQL'
-- Insert test company
INSERT INTO companies (id, name, careers_url, application_mode, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  'TechCorp Industries',
  'https://careers.techcorp.example.com',
  'global',
  NOW(),
  NOW()
) ON CONFLICT (name) DO NOTHING
RETURNING id;

-- Get the company ID for use in jobs
WITH company AS (
  SELECT id FROM companies WHERE name = 'TechCorp Industries' LIMIT 1
)
INSERT INTO jobs (id, company_id, title, url, raw_jd, status, found_at, created_at, updated_at)
SELECT
  gen_random_uuid(),
  company.id,
  'Senior Python Developer',
  'https://careers.techcorp.example.com/senior-python-dev',
  'Senior Python Developer - San Francisco, CA

We are looking for an experienced Senior Python Developer with 5+ years of professional experience.

Required Skills:
- 5+ years Python development experience
- Expert with FastAPI or Django
- PostgreSQL and Redis expertise
- Docker and Kubernetes
- AWS or GCP experience
- Strong system design background

Nice to Have:
- Experience with LLMs or AI
- Microservices architecture
- CI/CD pipelines
- GraphQL
- Async/await patterns

What we offer:
- Competitive salary: $160k-$200k
- Health insurance, 401k, dental
- Unlimited PTO
- Remote work options (hybrid)
- Learning budget $2000/year
- Stock options

This is a fully remote position. We support visa sponsorship. Interview process: 4 rounds over 3 weeks.',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company

UNION ALL

SELECT
  gen_random_uuid(),
  company.id,
  'Full Stack Engineer',
  'https://careers.techcorp.example.com/fullstack',
  'Full Stack Engineer - New York, NY

Looking for an experienced Full Stack Engineer to join our growing team building AI-powered applications.

Required:
- 3-7 years full stack development
- Python 3.8+
- React 18+ / TypeScript
- PostgreSQL
- REST APIs and microservices
- Git and code review best practices

Preferred:
- GraphQL experience
- Docker
- CI/CD familiarity
- Agile/Scrum experience

Salary: $130k-$170k
Benefits: Health insurance, 401k, 3 weeks PTO, learning budget
Work location: Hybrid (3 days office, 2 remote)
Visa sponsorship: YES',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company

UNION ALL

SELECT
  gen_random_uuid(),
  company.id,
  'Backend Engineer',
  'https://careers.techcorp.example.com/backend',
  'Backend Engineer - Remote

Building scalable backend services for our SaaS platform.

Requirements:
- 4+ years backend development
- Python or Go
- PostgreSQL, Redis
- Docker, Kubernetes
- DevOps experience
- 24/7 on-call rotation (monthly)

Responsibilities:
- Design and implement APIs
- Optimize database queries
- Implement caching strategies
- Code reviews and mentoring juniors
- Incident response

Salary: $140k-$180k
100% Remote
Visa: Available
Benefits: Health, dental, vision, 401k, unlimited PTO',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company

UNION ALL

SELECT
  gen_random_uuid(),
  company.id,
  'Lead Python Engineer',
  'https://careers.techcorp.example.com/lead-python',
  'Lead Python Engineer - Remote

Join our backend team as a technical leader!

Requirements:
- 8+ years Python development
- Team leadership experience (managing 3-5 engineers)
- Architecture and system design expertise
- Microservices and distributed systems
- Infrastructure and DevOps knowledge

Responsibilities:
- Lead technical direction of backend
- Mentor and manage engineering team
- Code architecture reviews
- Performance optimization
- Hiring and team growth

Salary: $180k-$250k
Equity: 0.1-0.5%
Remote: YES
Visa: Sponsored
Benefits: All inclusive - health insurance, 401k, learning budget $5000/yr, home office stipend',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company

UNION ALL

SELECT
  gen_random_uuid(),
  company.id,
  'Junior Developer',
  'https://careers.techcorp.example.com/junior',
  'Junior Developer (Recent Graduate) - Austin, TX

We''re looking for passionate junior developers! We train and mentor intensively.

Requirements:
- Recent bootcamp graduate or CS degree
- Knowledge of Python OR JavaScript
- Understanding of web basics (HTTP, REST)
- Willingness to learn
- Strong communication

What we''ll teach:
- Professional development practices
- Code review and Git workflows
- System design fundamentals
- Testing and debugging
- Agile methodologies

Salary: $70k-$90k
Internship to Full-Time pathway
Location: Austin, TX (flexible remote after 3 months)
Benefits: Health insurance, 401k, learning resources',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company

UNION ALL

SELECT
  gen_random_uuid(),
  company.id,
  'DevOps Engineer',
  'https://careers.techcorp.example.com/devops',
  'DevOps Engineer - Remote

Manage and optimize our cloud infrastructure.

Skills Needed:
- 3+ years DevOps /SRE experience
- Kubernetes administration
- AWS or GCP
- Infrastructure as Code (Terraform)
- CI/CD pipelines (Jenkins, GitLab CI)
- Monitoring and logging (Prometheus, ELK)

Salary: $140k-$180k
Remote: 100%
Visa: Available
Benefits: Health, dental, vision, 401k, unlimited PTO, $3000 learning budget',
  'new',
  NOW(),
  NOW(),
  NOW()
FROM company;

SELECT COUNT(*) as jobs_created FROM jobs WHERE status = 'new';
ENDSQL

echo "✅ Test jobs seeded successfully!"
echo ""
echo "Testing endpoints..."
echo ""

# Test health
echo "1. Health Check:"
curl -s http://localhost:8000/health | jq .

echo ""
echo "2. Job Stats:"
curl -s http://localhost:8000/jobs/stats/summary | jq .

echo ""
echo "3. List Jobs:"
curl -s http://localhost:8000/jobs | jq '.[] | {title: .title, url: .url}' | head -20
