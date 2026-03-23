#!/usr/bin/env python3
import os
import psycopg2
import json
import uuid

# Connect to database
conn = psycopg2.connect(
    host="localhost",
    port="5433",
    database="autoapply_db",
    user="autoapply",
    password="autoapply_dev_password"
)

cursor = conn.cursor()

# Test resume data
resume_data = {
    "text": "John Doe\nSenior Backend Engineer\n6+ years experience\n\nSkills: Python, FastAPI, PostgreSQL, Docker, Redis, AWS, Kubernetes\n\nExperience:\n- Senior Backend Engineer at TechStartup (2022-Present)\n- Backend Engineer at CloudServices (2019-2022)\n\nEducation: BS Computer Science\n\nPreferences: Remote/Hybrid, $150k-$200k, Tech/SaaS industries",
    "name": "John Doe",
    "email": "john@example.com",
    "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "AWS"],
    "experience_years": 6,
    "seniority_level": "senior",
    "current_title": "Senior Backend Engineer"
}

try:
    cursor.execute(
        """INSERT INTO resumes (id, base_resume, created_at, updated_at)
           VALUES (%s, %s, NOW(), NOW())
           ON CONFLICT DO NOTHING""",
        (str(uuid.uuid4()), json.dumps(resume_data))
    )
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM resumes")
    count = cursor.fetchone()[0]
    print(f"✅ Resume created successfully! Total resumes: {count}")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    cursor.close()
    conn.close()
