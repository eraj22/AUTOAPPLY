-- Check jobs with source (Phase 2 scraped)
SELECT COUNT(*) as jobs_with_source FROM jobs WHERE source IS NOT NULL;
SELECT COUNT(*) as total_jobs FROM jobs;

-- Show recent scraped jobs
SELECT id, title, source, location, external_job_id, scraped_at 
FROM jobs 
WHERE source IS NOT NULL 
ORDER BY scraped_at DESC LIMIT 10;
