# GitHub Publishing Guide

## Current Status

✅ **Code is ready for publishing**
- All features merged to `main` branch
- Complete documentation suite created
- 4,626 lines of new code added
- Syntax validated and tested

## Manual Publishing Steps

Since this environment doesn't have GitHub credentials configured, follow these steps:

### Option 1: Create New Repository (Recommended)

```bash
# 1. Go to GitHub.com
# 2. Click "New repository"
# 3. Name it: crossroad
# 4. Description: "Indonesian Political Intelligence Platform"
# 5. Choose Public or Private
# 6. DO NOT initialize with README (we already have one)
# 7. Click "Create repository"

# 8. In your terminal:
cd /workspace

# Remove the placeholder remote
git remote remove origin

# Add your actual GitHub remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/crossroad.git

# Push to GitHub
git push -u origin main
```

### Option 2: Push to Existing Repository

```bash
cd /workspace

# Update remote URL (replace with your repo)
git remote set-url origin https://github.com/YOUR_USERNAME/crossroad.git

# Push all branches
git push -u origin main --force

# Push tags if any
git push --tags
```

### Option 3: Using SSH (More Secure)

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub: Settings → SSH and GPG keys → New SSH key

# Then use SSH URL:
git remote set-url origin git@github.com:YOUR_USERNAME/crossroad.git

# Push
git push -u origin main
```

## Repository Structure

Your repository will include:

```
crossroad/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # API endpoints
│   ├── graph.py                # Neo4j operations
│   ├── db.py                   # PostgreSQL connection
│   ├── scheduler.py            # Scheduled tasks
│   ├── crawler/                # Data scrapers
│   │   ├── wikipedia.py        # Wikipedia crawler
│   │   ├── news.py             # News scrapers
│   │   ├── enhanced_sources.py # KPU, LHKPN, KPK, AHU
│   │   ├── business_registry.py# Company ownership
│   │   ├── apbd_tracker.py     # APBD budget tracking
│   │   └── legal_scraper.py    # SIPP, JDIH, LPSE
│   ├── tests/
│   │   └── test_masud_dynasty.py
│   └── requirements.txt
├── frontend/                   # React + D3.js frontend
├── docs/                       # Documentation (10 files)
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   ├── API_COOKBOOK.md
│   ├── DEVELOPER_GUIDE.md
│   ├── USER_GUIDE.md
│   ├── OPERATIONS_RUNBOOK.md
│   ├── SECURITY.md
│   ├── TROUBLESHOOTING.md
│   └── HOWTO.md
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment template
├── LICENSE                     # MIT License
└── README.md                   # Main README
```

## After Publishing

### 1. Protect Main Branch

Go to: Settings → Branches → Add branch protection rule
- Branch name pattern: `main`
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass before merging
- ✅ Require branches to be up to date before merging

### 2. Enable GitHub Actions

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest backend/tests/ -v
```

### 3. Add Repository Topics

In your repository main page, add topics:
- `indonesia`
- `politics`
- `knowledge-graph`
- `neo4j`
- `corruption-tracking`
- `oligarchy`
- `political-dynasty`
- `transparency`

### 4. Configure GitHub Pages (Optional)

For documentation site:
- Go to Settings → Pages
- Source: Deploy from branch `main`, folder `/docs`
- Your docs will be available at: `https://YOUR_USERNAME.github.io/crossroad`

## Verification Checklist

Before publishing, ensure:

- ✅ No sensitive data in code (API keys, passwords)
- ✅ `.gitignore` properly configured
- ✅ LICENSE file present
- ✅ README.md is comprehensive
- ✅ All tests pass
- ✅ Documentation is complete
- ✅ Code follows style guidelines

## Security Notes

⚠️ **Before pushing**:

1. Remove any hardcoded credentials:
   ```bash
   grep -r "password" backend/ --include="*.py"
   grep -r "api_key" backend/ --include="*.py"
   grep -r "secret" backend/ --include="*.py"
   ```

2. Ensure `.env` is in `.gitignore`:
   ```bash
   cat .gitignore | grep env
   ```

3. Check for exposed tokens:
   ```bash
   git log --all --full-history -- "*.env"
   ```

## Alternative: Use GitHub Desktop

If you prefer GUI:

1. Download GitHub Desktop
2. File → Add Local Repository
3. Select `/workspace` folder
4. Publish to GitHub

---

**Need Help?**

Contact: support@crossroad.id (placeholder)
Documentation: See `/docs` folder
