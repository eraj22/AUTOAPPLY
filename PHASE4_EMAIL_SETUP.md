"""
Phase 4 Testing Guide — Email Notifications System

SETUP STEPS:
============

1. GET RESEND API KEY
   - Go to https://resend.com
   - Sign up free account
   - Copy your API key
   - Update .env: RESEND_API_KEY=re_xxxxx

2. RUN DATABASE MIGRATION
   - psql -U autoapply -d autoapply_db -f /home/sher/autoapply/backend/migrate.sql
   - This creates email_logs table

3. RESTART BACKEND
   - docker restart autoapply-backend
   - Check logs: docker logs autoapply-backend

4. TEST EMAIL SENDING
   - Use the test endpoints below


TEST ENDPOINTS:
===============

(A) Send Approval Email Test:
POST /jobs/test-approval-email
{
    "to_email": "your-email@example.com",
    "job_id": "550e8400-e29b-41d4-a716-446655440000",  # Replace with real job ID
    "company_name": "TechCorp",
    "job_title": "Senior Backend Engineer",
    "fit_score": 87,
    "match_summary": "Perfect match for your Python and FastAPI expertise"
}

(B) Send Auto-Applied Email Test:
POST /jobs/test-auto-apply-email
{
    "to_email": "your-email@example.com",
    "job_id": "550e8400-e29b-41d4-a716-446655440001",
    "company_name": "Stripe",
    "job_title": "Backend Engineer",
    "fit_score": 92
}

(C) Send Confirmation Email Test:
POST /jobs/test-confirmation-email
{
    "to_email": "your-email@example.com",
    "job_id": "550e8400-e29b-41d4-a716-446655440002",
    "company_name": "Google",
    "job_title": "Senior Backend Engineer",
    "fit_score": 88
}

(D) Send Manual Required Email Test:
POST /jobs/test-manual-email
{
    "to_email": "your-email@example.com",
    "job_id": "550e8400-e29b-41d4-a716-446655440003",
    "company_name": "Meta",
    "job_title": "Backend Engineer",
    "issue_description": "Form submission required manual interaction"
}

(E) Send Daily Digest Email Test:
POST /jobs/test-digest-email
{
    "to_email": "your-email@example.com"
}


TESTING WORKFLOW:
==================

1. Get a real job ID from your seeded jobs:
   curl http://localhost:8000/jobs

2. Send an approval email:
   POST http://localhost:8000/jobs/test-approval-email
   
3. Check email at your recipient's inbox

4. Verify email_logs table:
   SELECT * FROM email_logs ORDER BY created_at DESC LIMIT 5;

5. Follow the approval link from email to trigger /approve endpoint

6. Check that job status changed to "applying" or "pending_approval"


DEBUGGING:
===========

- Check Resend API key in .env
- Verify docker backend is running: docker ps | grep autoapply-backend
- View backend logs: docker logs -f autoapply-backend
- Check database connection: psql -U autoapply -d autoapply_db -c "SELECT COUNT(*) FROM emails_logs;"
- Test Resend API directly with valid key


NEXT STEPS AFTER TESTING:
===========================

Once email system is working:

1. Create /jobs/send-approval-email endpoint that:
   - Generates JWT token with job_id and "approve" action
   - Creates URLs with signed tokens
   - Calls email_service.send_approval_email()

2. Integrate into job matching workflow:
   - When job found, generate token + URLs
   - Send approval email to user
   - Wait for /approve or /skip

3. Integrate into auto-apply workflow:
   - Send auto_applied email after successful submission
   - Send confirmation email with proof (screenshot)
   - Send manual_required email on failures

4. Setup scheduled task (Celery Beat) for:
   - Daily digest emails at 8 AM
   - Cleanup old email logs
"""
