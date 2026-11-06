# Prism Desk

**One Lab. Multiple Projects. Connected Research.**

Laboratory management and research collaboration platform for PRISM Laboratory: projects,
research literature (metadata and links only), tasks with versioned submissions, a daily research
handbook, conference deadlines, Discord notifications and role-specific dashboards.

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL (`backend/`)
- Frontend: React, TypeScript, Vite, Tailwind CSS (`frontend/`)
- Notifications: Discord bot + OAuth2 account linking (no internal chat, no file uploads)

## Quick start (development)
```bash
cd backend && python3 -m venv venv && venv/bin/pip install -r requirements.txt && cp .env.example .env
```
```bash
cd backend && venv/bin/alembic upgrade head && venv/bin/python -m scripts.create_admin
```
```bash
cd backend && venv/bin/uvicorn main:app --reload --port 8000
```
```bash
cd frontend && npm install && npm run dev
```

## Tests
```bash
cd backend && venv/bin/python -m pytest
```
```bash
cd frontend && npm test && npx tsc -b && npm run build
```

## Documentation
- [Implementation report and test results](docs/IMPLEMENTATION_REPORT.md)
- [Audit and plan](docs/IMPLEMENTATION_PLAN.md)
- [Database and ER diagram](docs/DATABASE.md)
- [API and authorization](docs/API.md), [endpoint list](docs/API_ENDPOINTS.md)
- [Deployment, backup and restore](docs/DEPLOYMENT.md)
- Phase 0 requirements: `Doc/`
