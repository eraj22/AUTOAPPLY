SELECT COUNT(*) as total_jobs FROM jobs;
SELECT title, source, location, scraped_at FROM jobs ORDER BY created_at DESC LIMIT 5;
