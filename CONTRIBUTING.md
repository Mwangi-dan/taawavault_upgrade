# Contributing to TaawaVault

## Development Setup

1. Fork the repository
2. Create a feature branch
3. Set up development environment:
   ```bash
   ./setup.sh
   ```
4. Make your changes
5. Run tests:
   ```bash
   python manage.py test
   ```
6. Submit a pull request

## Code Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for all functions and classes
- Keep functions focused and small

## Testing

- Write tests for all new features
- Maintain 80%+ code coverage
- Test security features thoroughly
- Test multi-tenant isolation

## Security

- Never commit secrets or API keys
- Review security implications of changes
- Test for SQL injection, XSS, CSRF vulnerabilities
- Verify RLS policies work correctly

## Documentation

- Update README.md for user-facing changes
- Update SRS document for architectural changes
- Add docstrings to new code
- Update API documentation
