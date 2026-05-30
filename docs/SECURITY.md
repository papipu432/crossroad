# CROSSROAD Security Policy

## Security Overview

CROSSROAD handles sensitive political intelligence data. This document outlines our security policies and procedures.

## Data Classification

| Classification | Description | Examples | Handling Requirements |
|----------------|-------------|----------|----------------------|
| **Public** | Information available publicly | News articles, Wikipedia | Standard security |
| **Internal** | Non-public operational data | User accounts, configurations | Access control required |
| **Confidential** | Sensitive personal data | LHKPN reports, legal cases | Encryption + access logs |
| **Restricted** | Highly sensitive intelligence | Ongoing investigations | Multi-factor auth + audit |

## Authentication & Authorization

### Password Policy

- Minimum 12 characters
- At least 1 uppercase, 1 lowercase, 1 number, 1 special character
- No dictionary words or common patterns
- Expire every 90 days
- No password reuse (last 10 passwords)

### Multi-Factor Authentication (MFA)

**Required for**:
- Admin accounts
- API access with write permissions
- Database direct access

**Supported methods**:
- TOTP (Google Authenticator, Authy)
- WebAuthn (FIDO2 security keys)
- SMS (fallback only)

### Role-Based Access Control (RBAC)

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Viewer** | Read-only access to public data | General users |
| **Analyst** | Read + query execution, report generation | Investigators |
| **Admin** | Full access except audit logs | System administrators |
| **Auditor** | Read audit logs, compliance reports | Compliance officers |

## Data Protection

### Encryption

**At Rest**:
- AES-256 encryption for all databases
- Encrypted file systems for sensitive storage
- Key rotation every 12 months

**In Transit**:
- TLS 1.3 for all communications
- HSTS enabled
- Certificate pinning for mobile apps

### Data Minimization

- Collect only necessary data
- Anonymize where possible
- Automatic deletion after retention period

### Personal Data Protection (PDP Law Compliance)

In compliance with UU 27/2022 (Indonesian Personal Data Protection Law):

**Data Subject Rights**:
- Right to access
- Right to correction
- Right to deletion
- Right to portability

**Legal Basis**:
- Public interest (political transparency)
- Legitimate interest (anti-corruption)
- Consent (for non-public figures)

## API Security

### Rate Limiting

| Endpoint Tier | Limit | Window |
|---------------|-------|--------|
| Public | 100 requests | per minute |
| Authenticated | 500 requests | per minute |
| Admin | 1000 requests | per minute |

### Input Validation

- All inputs validated against schema
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)
- CSRF protection (tokens for state-changing operations)

### API Token Management

- Tokens expire after 30 days
- Automatic rotation for service accounts
- Immediate revocation on suspicious activity
- Audit logging for all token usage

## Infrastructure Security

### Network Security

- VPC isolation for all services
- Security groups with least-privilege access
- WAF (Web Application Firewall) for public endpoints
- DDoS protection

### Container Security

- Regular vulnerability scanning
- Minimal base images (Alpine Linux)
- Non-root containers
- Image signing and verification

### Secrets Management

- No secrets in code or config files
- HashiCorp Vault for production
- Docker secrets for development
- Automatic rotation

## Monitoring & Detection

### Security Monitoring

**Real-time alerts for**:
- Failed login attempts (>5 in 5 minutes)
- Unusual API access patterns
- Data exfiltration attempts
- Privilege escalation attempts

### Log Management

- Centralized logging (ELK stack)
- Immutable log storage
- Retention: 2 years minimum
- Access logging for all sensitive operations

### Intrusion Detection

- Fail2ban for SSH protection
- OSSEC for host-based IDS
- Network traffic analysis
- File integrity monitoring

## Incident Response

### Incident Classification

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | Active breach, data leak | Immediate (<15 min) |
| **High** | Attempted breach, vulnerability exploited | <1 hour |
| **Medium** | Policy violation, suspicious activity | <4 hours |
| **Low** | Minor security issue | <24 hours |

### Response Procedure

1. **Identification**: Detect and classify incident
2. **Containment**: Isolate affected systems
3. **Eradication**: Remove threat
4. **Recovery**: Restore normal operations
5. **Lessons Learned**: Post-incident review

### Breach Notification

In case of personal data breach:
- Notify affected individuals within 72 hours
- Report to Indonesian PDP Authority (Kominfo)
- Document all actions taken

## Vulnerability Management

### Scanning Schedule

- **Daily**: Automated vulnerability scans
- **Weekly**: Dependency updates
- **Monthly**: Penetration testing
- **Quarterly**: Third-party security audit

### Patch Management

- **Critical**: Within 24 hours
- **High**: Within 7 days
- **Medium**: Within 30 days
- **Low**: Next maintenance window

### Responsible Disclosure

We welcome security research! Please report vulnerabilities to:

- Email: security@crossroad.id
- PGP Key: [Download](https://crossroad.id/security-pgp.asc)
- Response time: Within 48 hours

**Please include**:
- Description of vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if any)

## Compliance

### Regulatory Compliance

- ✅ UU 27/2022 (Indonesian PDP Law)
- ✅ ISO 27001 (Information Security Management)
- ✅ OWASP Top 10 (Web Application Security)
- ⏳ SOC 2 Type II (in progress)

### Audit Trail

All security-relevant events logged:
- Authentication attempts
- Authorization decisions
- Data access
- Configuration changes
- Administrative actions

## Security Training

### Required Training

- **All employees**: Annual security awareness
- **Developers**: Secure coding practices
- **Operations**: Incident response procedures
- **Management**: Risk management

### Phishing Tests

- Quarterly simulated phishing campaigns
- Immediate training for failures
- Metrics tracking and improvement

## Physical Security

### Data Center Requirements

- 24/7 surveillance
- Biometric access control
- Environmental controls
- Redundant power and cooling

### Device Security

- Full disk encryption on all devices
- Remote wipe capability
- No local storage of sensitive data
- Clean desk policy

## Business Continuity

### Backup Strategy

- Daily incremental backups
- Weekly full backups
- Off-site replication
- Quarterly restore tests

### Disaster Recovery

- RTO: 4 hours
- RPO: 24 hours
- Secondary site availability
- Regular DR drills

## Third-Party Risk Management

### Vendor Assessment

Before engaging vendors:
- Security questionnaire
- Compliance verification
- Contract with security clauses
- Regular audits

### Data Sharing Agreements

- Define data usage limitations
- Specify security requirements
- Include breach notification terms
- Regular compliance reviews

## Contact

**Security Team**:
- Email: security@crossroad.id
- Emergency: +62-xxx-xxxx-xxxx (24/7)
- PGP Key: Available on website

**Reporting Hours**:
- Normal: 09:00-17:00 WIB (Mon-Fri)
- Emergency: 24/7

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Next Review**: Q2 2025  
**Owner**: Chief Security Officer
