-- Add missing columns to jobs table for Phase 3A
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS parser_version VARCHAR DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS parsed_at TIMESTAMP DEFAULT NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS match_score INTEGER DEFAULT NULL;

-- Phase 4: Email Notifications System
-- Create email_logs table to track all sent emails
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    to_email VARCHAR(255) NOT NULL,
    email_type VARCHAR(50) NOT NULL,
    job_id UUID,
    subject VARCHAR(255) NOT NULL,
    resend_id VARCHAR(255),
    sent_at TIMESTAMP,
    deliver_status VARCHAR(50),
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
);

-- Create index on to_email and email_type for faster queries
CREATE INDEX IF NOT EXISTS idx_email_logs_to_email ON email_logs(to_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_type ON email_logs(email_type);
CREATE INDEX IF NOT EXISTS idx_email_logs_job_id ON email_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at);

