# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of RAE seriously. If you discover a security vulnerability, please follow these steps:

### 1. DO NOT Open a Public Issue

Please do not open a public GitHub issue for security vulnerabilities. This could put all users at risk.

### 2. Report Privately

Send a detailed report to: **lesniowskig@gmail.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

### 3. Response Timeline

- **Initial Response:** Within 48 hours
- **Status Update:** Within 7 days
- **Fix Timeline:** Depends on severity
  - Critical: 24-48 hours
  - High: 7 days
  - Medium: 30 days
  - Low: Next release

### 4. Disclosure Policy

- **Embargo Period:** We request a 90-day embargo period before public disclosure to allow users to upgrade.
- We will acknowledge your email within 48 hours
- We will provide a more detailed response within 7 days

## ISO 27001 Compliance

RAE-Core is being developed in accordance with ISO/IEC 27001:2022 standards.
See our [ISO 27001 Implementation Plan](docs/compliance/ISO_27001_IMPLEMENTATION_PLAN.md) for details on:
- Secure Development Lifecycle (SDLC)
- Access Control
- Cryptography
- Operations Security

## Security Best Practices

When deploying RAE, please follow our [Security and Multi-Tenancy Guide](docs/guides/security-and-multi-tenancy.md).

### Quick Checklist

- [ ] Use JWT authentication in production (not API keys)
- [ ] Enable HTTPS/TLS for all connections
- [ ] Use strong secrets (32+ characters, random)
- [ ] Enable rate limiting
- [ ] Keep dependencies updated
- [ ] Use PostgreSQL Row Level Security
- [ ] Implement proper logging and monitoring
- [ ] Regular security audits
- [ ] Use secrets management (Vault, AWS Secrets Manager, etc.)

## Known Security Considerations

### Database Access

RAE uses PostgreSQL with Row Level Security (RLS) for multi-tenant isolation. Ensure:
- RLS policies are enabled on all tenant tables
- Database credentials are properly secured
- Connection pooling limits are configured

### API Authentication

RAE supports:
- API Key authentication (for internal services only)
- JWT/OAuth2 (recommended for production)

**Never use API keys in production for external-facing APIs.**

### Third-Party Dependencies

We regularly scan dependencies for vulnerabilities using:
- GitHub Dependabot
- `safety check` (Python)
- `npm audit` (JavaScript integrations)

Run `make security-check` to scan for vulnerabilities.

## Security Features

RAE includes built-in security features:

- **Multi-Tenancy:** Complete data isolation per tenant
- **Row Level Security:** Database-level access control
- **Rate Limiting:** Prevent abuse and DoS attacks
- **PII Scrubbing:** Automatic detection and removal of sensitive data
- **Audit Logging:** Track all operations
- **Input Validation:** Pydantic-based request validation
- **CORS Protection:** Configurable origin restrictions

## Compliance

### GDPR

RAE provides endpoints for GDPR compliance:
- Right to erasure (DELETE user data)
- Right to access (GET user data export)
- Data portability (JSON/CSV export)

### SOC 2

RAE is designed with SOC 2 principles in mind:
- Security logging
- Access controls
- Data encryption
- Backup procedures

## Hall of Fame

We appreciate security researchers who help keep RAE secure:

<!-- Security researchers will be listed here after responsible disclosure -->

## Contact

For security concerns: lesniowskig@gmail.com

For general questions: GitHub Issues

---

Thank you for helping keep RAE and our users safe!
