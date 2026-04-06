-- Check if Phase 2 columns exist in jobs table
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'jobs' 
AND column_name IN ('source', 'external_job_id', 'location', 'scraped_at')
ORDER BY column_name;
