.PHONY: build test sync migrate run-api run-ui run-bot

build:
	docker compose build

test:
	docker compose run --rm backend pytest tests/ -v

test-tools:
	docker compose run --rm backend pytest tests/test_agent_tools.py -v

test-memory:
	docker compose run --rm backend pytest tests/test_memory_extraction.py -v

test-calendar:
	docker compose run --rm backend pytest tests/test_calendar_backend.py -v

sync:
	docker compose run --rm backend python scripts/run_live_sync.py

migrate:
	docker compose run --rm backend python scripts/migrate_add_study_time.py

run-api:
	docker compose run --rm -p 8000:8000 backend uvicorn src.api:app --host 0.0.0.0 --port 8000

run-ui:
	docker compose run --rm -p 7860:7860 backend python app/main.py

shell:
	docker compose run --rm backend bash

db-shell:
	docker compose run --rm backend sqlite3 data/student_context.db

clean:
	docker compose down -v
	rm -f data/student_context.db