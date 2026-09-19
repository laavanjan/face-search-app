.PHONY: install-backend install-frontend dev-backend dev-frontend test up down

install-backend:
	cd backend && python -m venv .venv && . .venv/Scripts/activate && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest

up:
	docker compose up --build

down:
	docker compose down
