# TaawaVault Deployment Guide

## Production Deployment Checklist

### 1. Environment Setup

1. **Set Environment Variables**:
   - Copy `.env.example` to `.env`
   - Set `DEBUG=False`
   - Set strong `SECRET_KEY`
   - Configure database credentials
   - Set `ALLOWED_HOSTS` to your domain

2. **Database Setup**:
   ```bash
   # Create PostgreSQL database
   createdb taawavault
   
   # Run migrations
   python manage.py migrate
   
   # Set up RLS policies (see SRS Section 8)
   ```

3. **Static Files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

### 2. PostgreSQL RLS Configuration

After migrations, run these SQL commands:

```sql
-- Enable RLS
ALTER TABLE core_ledgerentry ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_membership ENABLE ROW LEVEL SECURITY;
ALTER TABLE core_group ENABLE ROW LEVEL SECURITY;

-- Create policies (see core/migrations for full implementation)
```

### 3. Redis Setup

```bash
# Install Redis
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis
```

### 4. Celery Setup

```bash
# Start Celery worker
celery -A config worker -l info

# Start Celery beat (for scheduled tasks)
celery -A config beat -l info
```

### 5. Gunicorn Setup

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 6. Nginx Configuration

Example Nginx config:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/taawavault/staticfiles/;
    }

    location /media/ {
        alias /path/to/taawavault/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 7. SSL/TLS Setup

Use Let's Encrypt:

```bash
sudo certbot --nginx -d your-domain.com
```

### 8. Systemd Service Files

Create `/etc/systemd/system/taawavault.service`:

```ini
[Unit]
Description=TaawaVault Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/taawavault
ExecStart=/path/to/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 4

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/taawavault-celery.service`:

```ini
[Unit]
Description=TaawaVault Celery worker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/taawavault
ExecStart=/path/to/venv/bin/celery -A config worker -l info

[Install]
WantedBy=multi-user.target
```

### 9. Monitoring

- Set up application monitoring (Datadog, New Relic, Sentry)
- Configure log aggregation (ELK stack, CloudWatch)
- Set up health checks
- Configure alerting

### 10. Backup Strategy

- Daily database backups
- File storage backups (S3 versioning)
- Test restore procedures regularly

## Docker Deployment

### Using Docker Compose

```bash
docker-compose up -d
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (to be created).

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY`
- [ ] HTTPS enabled
- [ ] Security headers configured
- [ ] Database credentials secured
- [ ] API keys in secrets manager
- [ ] File upload limits enforced
- [ ] Rate limiting enabled
- [ ] Audit logging operational
- [ ] RLS policies tested
- [ ] Encryption keys secured

## Performance Optimization

- [ ] Redis caching enabled
- [ ] Database connection pooling (PgBouncer)
- [ ] Static files on CDN
- [ ] Database indexes created
- [ ] Materialized views refreshed
- [ ] Celery workers scaled

## Compliance

- [ ] Consent management operational
- [ ] DPA system configured
- [ ] Audit logs retained (7 years)
- [ ] Data residency enforced
- [ ] PII encryption verified
