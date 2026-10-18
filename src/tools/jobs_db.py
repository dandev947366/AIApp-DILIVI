from datetime import datetime
from src.database import SessionLocal
from src.models.job_models import JobModel, JobCollectionRunModel


def save_jobs_to_db(jobs_data: list[dict]) -> int:
    """Saves fetched jobs to the database, skipping duplicates."""
    jobs_added = 0
    with SessionLocal() as db:
        for job in jobs_data:
            url = job.get("url")
            if not url:
                continue

            # Skip if job already exists in DB
            if db.query(JobModel).filter_by(url=url).first():
                continue

            # Helper to format lists to strings (Jobicy sometimes returns lists)
            def _as_text(val):
                if isinstance(val, list):
                    return ", ".join(str(v) for v in val)
                return str(val) if val else ""

            new_job = JobModel(
                title=_as_text(job.get("jobTitle")) or "Unknown Title",
                company=_as_text(job.get("companyName")),
                location=_as_text(job.get("jobGeo")),
                country=_as_text(job.get("jobGeo")),  # Grouping by this in the UI
                url=url,
                industry=_as_text(job.get("jobIndustry")),
                salary=f"{job.get('salaryMin', '')}-{job.get('salaryMax', '')} {job.get('salaryCurrency', '')}".strip(
                    "- "
                ),
            )
            db.add(new_job)
            jobs_added += 1

        # Log the run for the Health panel
        run_log = JobCollectionRunModel(
            status="success", jobs_added=jobs_added, run_at=datetime.utcnow()
        )
        db.add(run_log)
        db.commit()

    return jobs_added
