# CROSSROAD Operations Runbook

## Production Deployment

### Prerequisites

- Server with 16GB+ RAM, 4+ CPU cores
- Docker & Docker Compose installed
- Domain name configured (optional)
- SSL certificate (Let's Encrypt recommended)

### Deployment Steps

```bash
# 1. Clone repository
git clone https://github.com/your-org/crossroad.git
cd crossroad

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with production values

# 3. Create production docker-compose override
cat > docker-compose.prod.yml << EOF
version: '3.8'
services:
  backend:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    restart: always
    
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=2G
      - NEO4J_dbms_memory_heap_max__size=4G
    volumes:
      - neo4j_data:/data
    restart: always

volumes:
  neo4j_data:
EOF

# 4. Deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 5. Check status
docker compose ps

# 6. View logs
docker compose logs -f backend
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Neo4j health
curl http://localhost:7474/browser/

# Redis health
redis-cli ping

# PostgreSQL health
pg_isready -h localhost -U postgres
```

### Key Metrics to Monitor

| Metric | Threshold | Alert Level |
|--------|-----------|-------------|
| Neo4j Memory Usage | > 80% | WARNING |
| Neo4j Heap Usage | > 90% | CRITICAL |
| API Response Time | > 2s | WARNING |
| Error Rate | > 5% | CRITICAL |
| Disk Usage | > 85% | WARNING |
| Queue Length | > 1000 | WARNING |

### Log Aggregation

```bash
# Install Prometheus + Grafana
docker compose -f monitoring.yml up -d

# Access Grafana
open http://localhost:3001
# Username: admin, Password: admin
```

## Backup Strategy

### Automated Backups

```bash
# Create backup script
cat > /usr/local/bin/crossroad-backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups/crossroad/$DATE

mkdir -p $BACKUP_DIR

# Neo4j backup
docker exec neo4j neo4j-admin dump --database=neo4j --to-path=/backups
docker cp neo4j:/var/lib/neo4j/backups/neo4j.dump $BACKUP_DIR/

# PostgreSQL backup
docker exec postgres pg_dump -U postgres crossroad > $BACKUP_DIR/postgres.sql

# ChromaDB backup
docker cp chromadb:/chroma/chroma.sqlite3 $BACKUP_DIR/

# Compress
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR.tar.gz s3://your-bucket/backups/

# Keep only last 7 days
find /backups/crossroad -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /usr/local/bin/crossroad-backup.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/crossroad-backup.sh" | crontab -
```

### Restore from Backup

```bash
# Download backup
wget https://your-backup-url/crossroad_20240101_020000.tar.gz

# Extract
tar -xzf crossroad_20240101_020000.tar.gz

# Stop services
docker compose down

# Restore Neo4j
docker cp neo4j.dump neo4j:/var/lib/neo4j/backups/
docker exec neo4j neo4j-admin load --database=neo4j --from-path=/backups --force

# Restore PostgreSQL
cat postgres.sql | docker exec -i postgres psql -U postgres -d crossroad

# Restore ChromaDB
docker cp chroma.sqlite3 chromadb:/chroma/

# Start services
docker compose up -d
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  backend:
    deploy:
      replicas: 5
      
  redis:
    image: redis:7-cluster
    command: redis-server --cluster-enabled yes
    
  neo4j:
    # Use Neo4j Causal Cluster for production
    image: neo4j:5.23-enterprise
```

### Load Balancing

```nginx
# nginx.conf
upstream crossroad_backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    listen 443 ssl;
    server_name crossroad.yourdomain.com;
    
    location / {
        proxy_pass http://crossroad_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Incident Response

### Common Issues

#### Neo4j Out of Memory

**Symptoms**: Slow queries, connection timeouts

**Resolution**:
```bash
# Increase heap size
docker compose stop neo4j
# Edit .env: NEO4J_dbms_memory_heap_max__size=8G
docker compose up -d neo4j

# Clear query cache
MATCH (n) DETACH DELETE n WHERE n.temp = true
```

#### Scheduler Stuck

**Symptoms**: Tasks not running, progress stalled

**Resolution**:
```bash
# Restart scheduler
docker compose restart scheduler

# Clear Redis queue
redis-cli FLUSHDB

# Check task status
curl http://localhost:8000/api/scheduler/status
```

#### Scraper Blocked

**Symptoms**: HTTP 429 errors, CAPTCHA challenges

**Resolution**:
```bash
# Rotate IP addresses
# Update proxy list in .env

# Reduce request rate
# Update RATE_LIMIT_PER_MINUTE=50

# Add delays in scraper
# Edit crawler/base.py:增加 sleep time
```

### Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-call Engineer | oncall@crossroad.id | Immediate |
| Tech Lead | techlead@crossroad.id | 30 minutes |
| CTO | cto@crossroad.id | 1 hour |

## Security Updates

### Regular Maintenance

```bash
# Weekly: Update dependencies
pip install --upgrade -r requirements.txt
npm update

# Monthly: Security audit
pip-audit
npm audit

# Quarterly: Penetration testing
# Hire external security firm
```

### Vulnerability Response

1. **Identify**: Monitor CVE databases, GitHub Security Advisories
2. **Assess**: Determine impact on CROSSROAD
3. **Patch**: Apply updates within SLA (Critical: 24h, High: 7d)
4. **Test**: Verify fixes in staging environment
5. **Deploy**: Roll out to production
6. **Report**: Document incident and lessons learned

## Performance Tuning

### Neo4j Optimization

```cypher
// Create indexes for common queries
CREATE INDEX FOR (p:Person) ON (p.slug);
CREATE INDEX FOR (c:Company) ON (c.npwb);
CREATE FULLTEXT INDEX entityNames FOR (p:Person|c:Company) ON EACH [p.name, c.name];

// Optimize query planning
EXPLAIN MATCH (p:Person)-[:OWNS_SHARES]->(c:Company) 
WHERE p.name = "Rudy Mas'ud" 
RETURN p, c;
```

### Caching Strategy

```python
# Redis cache configuration
REDIS_CONFIG = {
    'default_timeout': 300,  # 5 minutes
    'person_profile_timeout': 3600,  # 1 hour
    'oligarchy_score_timeout': 86400,  # 24 hours
}
```

## Disaster Recovery

### RTO/RPO Targets

- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 24 hours

### DR Procedure

1. **Activate DR Site**: Switch to backup infrastructure
2. **Restore Data**: From latest backup
3. **Verify Integrity**: Run data validation checks
4. **Resume Services**: Bring applications online
5. **Communicate**: Notify stakeholders
6. **Post-Mortem**: Document and improve

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Review Cycle**: Quarterly
