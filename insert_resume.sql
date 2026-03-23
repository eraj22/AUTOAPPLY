-- Insert test resume
INSERT INTO resumes (id, base_resume, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  jsonb_build_object(
    'text', 'Senior Backend Engineer with 6 years of Python experience. Strong background in FastAPI, PostgreSQL, Docker, Redis, and AWS. Looking for senior level positions in remote or hybrid setup.',
    'skills', jsonb_build_array('Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis', 'AWS', 'Kubernetes'),
    'experience_years', 6,
    'seniority_level', 'senior',
    'current_title', 'Senior Backend Engineer',
    'name', 'John Doe'
  ),
  NOW(),
  NOW()
) ON CONFLICT DO NOTHING;

SELECT COUNT(*) as resumes_created FROM resumes;
