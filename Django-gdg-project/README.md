# University Library Management System (LMS)

Deployed: https://gdg-django-week-6.onrender.com/

A Django-based Library Management System that handles books, members, loans, loan requests, notifications, and fines, with role-based dashboards (member, staff, admin) and a JSON/REST API.

---

## Quick Links
- Live deployment: https://gdg-django-week-6.onrender.com/
- API root: `/api/v1/`
- Admin: `/admin/`

---

## Overview
LMS is built with Django and Django REST Framework to provide both HTML views and a RESTful API for library operations. It includes management commands for maintenance tasks and background workflows for loan expirations and overdue notifications.

## Features
- Book, author, and category management with availability tracking.
- Loan request workflow (request → staff review → approve/reject → pickup → loan lifecycle).
- Fine and transaction handling with payment endpoints.
- Role-based dashboards and authentication (session + JWT).
- Management commands for seeding data, creating roles, expiring pickups, and notifying overdue loans.

---

## Project Layout
Top-level important folders and files (relative to repository root):

- `my_first_project/`
  - `lmsProject/` — Django project configuration (settings, wsgi/asgi, urls)
    - `manage.py` — Django management shim for this project
    - `requirements.txt` — Python dependencies for this project
    - `Procfile`, `render.yaml` — deployment config for Render
  - `lmsApp/` — main application
    - `models.py` — database models (`Book`, `User/Member`, `Loan`, `LoanRequest`, `Transaction`)
    - `AccountView.py`, `bookViews.py`, `authorViews.py`, `memberLoanRequestViews.py`, `staffLoanRequestView.py` — view logic
    - `api_views.py`, `api_urls.py` — REST API viewsets and routers
    - `management/commands/` — cron/maintenance commands (seed data, expire loans, notify)
    - `Static/` and `templates/` — static assets and templates
- `docs/` — documentation and architecture diagrams

(See the repository tree for full detail.)

---

## Environment & Configuration
The project reads configuration from environment variables and a `.env` file when present. Important variables:

- `SECRET_KEY` — Django secret key (required in production)
- `DEBUG` — `true`/`false`
- `DATABASE_URL` — optional PostgreSQL URL for production (if absent, defaults to SQLite)
- `ALLOWED_HOSTS` — comma-separated hostnames
- `CSRF_TRUSTED_ORIGINS` — trusted origins for CSRF

---

## Local Development Quickstart
1. Clone the repo and create a virtual environment:

```bash
git clone <repo-url>
cd Django-gdg-project
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
```

2. Install dependencies and set up the database:

```bash
pip install -r my_first_project/lmsProject/requirements.txt
cd my_first_project/lmsProject
python manage.py migrate
python manage.py create_roles   # optional: create default roles/users
python manage.py collectstatic --noinput
python manage.py runserver
```

3. Access the app at `http://127.0.0.1:8000/` and admin at `http://127.0.0.1:8000/admin/`.

---

## Deployment (Render)
The Render configuration is provided in `my_first_project/lmsProject/render.yaml`. The build and start commands used on Render are:

- Build: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic`
- Start: `gunicorn lmsProject.wsgi:application --bind 0.0.0.0:$PORT --chdir /opt/render/project/src/Django-gdg-project/my_first_project/lmsProject`

Ensure `SECRET_KEY` and `DATABASE_URL` (if using Postgres) are set in the Render environment.

---

## API Documentation (Selected Endpoints)
Base API path: `/api/v1/`

Authentication:
- `POST /api/token/` — Obtain JWT tokens (also available at `/api/v1/auth/token/`)
  - Body: `{ "username": "<user>", "password": "<pass>" }`
  - Response: `{ "access": "<jwt>", "refresh": "<jwt_refresh>" }`
- `POST /api/token/refresh/` — Refresh access token

Auth helpers (API):
- `POST /api/v1/auth/register/` — Register a new user (see request fields in `lmsApp.api_views.register_api`)
- `POST /api/v1/auth/login/` — Login via API (returns session info / token)

Resource collections (list, create, retrieve, update, delete where supported):
- `GET/POST /api/v1/authors/` — Authors
- `GET/POST /api/v1/categories/` — Categories
- `GET/POST /api/v1/books/` — Books
- `GET/POST /api/v1/members/` — Members
- `GET/POST /api/v1/loans/` — Loans
- `GET/POST /api/v1/loan-requests/` — Loan requests
- `GET/POST /api/v1/transactions/` — Transactions
- `GET/POST /api/v1/notifications/` — Notifications

Health and utility endpoints:
- `GET /api/v1/health/` — Health check
- `GET /api/v1/` — DRF browsable API root (lists routers)

Example: get books with JWT

```bash
# obtain token
curl -X POST https://gdg-django-week-6.onrender.com/api/token/ -d "username=admin&password=pass"
# use token
curl -H "Authorization: Bearer <access_token>" https://gdg-django-week-6.onrender.com/api/v1/books/
```

For exact field names and payloads, refer to the serializers defined in `lmsApp/serrializer.py` and viewset docstrings in `lmsApp/api_views.py`.

---

## Management Commands
- `python manage.py create_roles` — ensure default roles/users exist
- `python manage.py seed_sample_data` — (if present) seed development data
- `python manage.py expire_loans` — expire uncollected approvals
- `python manage.py notify_overdue` — enqueue/send overdue notifications

---

## Contributing
- Fork the repo, create a feature branch, and open a PR with a clear description.
- Add tests for new behaviors and run `python manage.py test` where applicable.

---

## License & Contact
See `LICENSE` at the repository root. For questions, open an issue or contact the maintainer.
