# TaawaVault

Production-ready financial management system for groups, cooperatives, and savings clubs.

## Features

- **Double-Entry Accounting**: Immutable, append-only ledger with cryptographic hash chain
- **Multi-Tenant Isolation**: PostgreSQL Row-Level Security (RLS) for complete data isolation
- **Financial Integrity**: Database constraints, pessimistic locking, and transaction idempotency
- **Compliance**: Kenya DPA, GDPR, SOX compliance built-in
- **Security**: Field-level encryption, OAuth hardening, rate limiting, audit logging
- **Performance**: Redis caching, Celery async tasks, materialized views
- **Modern UI**: Dark theme dashboard inspired by modern design systems

## Technology Stack

- **Backend**: Django 5.2.6, Django REST Framework
- **Database**: PostgreSQL 14+ (required)
- **Cache/Tasks**: Redis, Celery
- **Authentication**: Django Allauth (Google OAuth), JWT
- **File Storage**: AWS S3 / Google Cloud Storage
- **AI Analytics**: Google Gemini API

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Virtual environment (recommended)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd taawavault_upgrade
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=taawavault
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Collect static files:
```bash
python manage.py collectstatic
```

8. Run development server:
```bash
python manage.py runserver
```

9. Run Celery worker (in separate terminal):
```bash
celery -A config worker -l info
```

## Database Setup

### PostgreSQL RLS Setup

After running migrations, set up Row-Level Security:

```sql
-- Enable RLS on tenant-scoped tables
ALTER TABLE core_ledgerentry ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_group ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (see migrations or SRS document)
```

### Database Constraints

The system includes:
- CHECK constraints for positive balances
- UNIQUE constraints for transaction idempotency
- Foreign key constraints for referential integrity
- Database triggers for balance updates

## API Documentation

API endpoints are available at `/api/v1/`:

- `GET /api/v1/groups/` - List groups
- `POST /api/v1/groups/` - Create group
- `GET /api/v1/groups/{id}/balance/` - Get group balance
- `POST /api/v1/ledger/contribution/` - Create contribution
- `POST /api/v1/ledger/expense/` - Create expense
- `POST /api/v1/token/` - Obtain JWT token

## Architecture

The system follows a layered architecture:

1. **Presentation Layer**: Django templates + HTML/CSS/JavaScript
2. **View Layer**: Function-based and class-based views
3. **Business Logic Layer**: Model methods + services
4. **Service Layer**: Financial, Notification, AI Analytics, Reports
5. **Event Sourcing Layer**: Immutable event store
6. **Data Access Layer**: Django ORM + PostgreSQL RLS
7. **Database Layer**: PostgreSQL with constraints and triggers

## Security Features

- Field-level encryption for PII (django-fernet-fields)
- Row-Level Security (RLS) for multi-tenant isolation
- OAuth state hardening (cryptographic signing)
- Rate limiting (per endpoint, per IP, per user)
- Comprehensive audit logging
- CSRF and XSS protection
- File upload validation and virus scanning

## Compliance

- **Kenya DPA Act 2019**: Consent management, DPA system, data residency
- **GDPR**: Encryption, access controls, audit logging
- **SOX**: Double-entry accounting, immutable records, 7-year retention
- **PCI DSS**: Comprehensive audit logging

## Testing

Run tests:
```bash
python manage.py test
```

## Production Deployment

See SRS document Section 18 for deployment architecture:
- Docker containerization
- Kubernetes manifests
- CI/CD pipeline
- Health checks
- Monitoring and observability

## Documentation

Full system specifications available in `SYSTEMS_SPECIFICATIONS_V2.md`.

## License

[Your License Here]

## Support

For issues and questions, please contact [Your Support Contact].
