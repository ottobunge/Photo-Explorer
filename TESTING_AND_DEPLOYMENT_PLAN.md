# Testing and Deployment Plan

**Status:** In Progress
**Created:** 2025-11-24

This document tracks the remaining work needed before pushing to GitHub and deploying to production.

---

## Current Blockers

### ❌ BLOCKER-1: NumPy/PyTorch Environment Issues
**Issue:** Tests cannot run in current NixOS environment due to missing libstdc++.so.6

**Error:**
```
ImportError: libstdc++.so.6: cannot open shared object file: No such file or directory
```

**Impact:** Cannot run unit or integration tests that import ML models

**Solutions:**
1. **Option A (Recommended):** Run tests in Docker container
   ```bash
   docker-compose run --rm backend pytest tests/
   ```

2. **Option B:** Fix NixOS environment with proper shell.nix
   ```nix
   { pkgs ? import <nixpkgs> {} }:
   pkgs.mkShell {
     buildInputs = with pkgs; [
       python312
       poetry
       stdenv.cc.cc.lib  # Provides libstdc++.so.6
     ];

     shellHook = ''
       export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
     '';
   }
   ```

3. **Option C:** Create test fixtures that mock ML services
   - Skip actual ML model loading in tests
   - Use pre-computed embeddings for test data

**Action:** Choose and implement one of the solutions above

---

## Testing Checklist

### ✅ Unit Tests (Created - Need Environment Fix)
- [x] Domain entities tests (Album, Connector, Face)
- [x] Repository tests (AlbumRepository)
- [x] ML services tests (with mocks)
- [x] Vector store tests (with mocks)
- [x] Worker task tests
- [x] Input validation tests
- [ ] **BLOCKED:** Run all unit tests and verify they pass

**Location:** `backend/tests/unit/`
**Command:** `pytest tests/unit/ -v`
**Status:** Created but cannot run due to environment issue

### ✅ Integration Tests (Created - Need Environment Fix)
- [x] Photo processing flow (upload → thumbnail → embedding)
- [x] Search flow (semantic search with CLIP)
- [x] Album management (CRUD operations)
- [x] Face detection and clustering
- [x] Google Photos sync (mocked API)
- [ ] **BLOCKED:** Run all integration tests and verify they pass

**Location:** `backend/tests/integration/`
**Command:** `pytest tests/integration/ -v`
**Status:** Created but cannot run due to environment issue

### ⏳ E2E Tests (To Be Created)
Priority: Test core semantic features and local file operations

**Required E2E Tests:**

1. **Semantic Search E2E**
   - [ ] Upload multiple photos via API
   - [ ] Wait for processing (embeddings generated)
   - [ ] Perform semantic search with text query
   - [ ] Verify results ranked by relevance
   - [ ] Test filter by connector/album
   - [ ] Test pagination

2. **Local File Upload E2E**
   - [ ] Upload photo from local filesystem
   - [ ] Verify thumbnail generation
   - [ ] Verify EXIF extraction
   - [ ] Verify face detection
   - [ ] Verify embedding creation
   - [ ] Search for uploaded photo

3. **Face Detection E2E**
   - [ ] Upload photos with faces
   - [ ] Verify face detection runs
   - [ ] Verify face embeddings created
   - [ ] Verify clustering groups similar faces
   - [ ] Search by face similarity

4. **Album Operations E2E**
   - [ ] Create album
   - [ ] Add photos to album
   - [ ] Filter search by album
   - [ ] Remove photos from album
   - [ ] Delete album

5. **Similar Photos E2E**
   - [ ] Upload reference photo
   - [ ] Get similar photos endpoint
   - [ ] Verify results are visually similar

**Location:** `backend/tests/e2e/` (to be created)
**Framework:** pytest + FastAPI TestClient + real database
**Status:** Not started

---

## Test Infrastructure Needs

### Required Services for E2E Tests
- [ ] PostgreSQL (test database)
- [ ] Qdrant (test collection)
- [ ] Redis (test instance)
- [ ] File storage (temp directory)

**Recommendation:** Use Docker Compose test profile
```yaml
# Add to docker-compose.yml
profiles:
  - test

services:
  test-backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://test:test@test-postgres:5432/test_db
      QDRANT_URL: http://test-qdrant:6333
    depends_on:
      - test-postgres
      - test-qdrant
    command: pytest tests/ -v
    profiles:
      - test
```

---

## Pre-Push Checklist

### Code Quality
- [x] Pre-commit hooks configured
- [x] .gitignore comprehensive
- [x] No secrets in repository
- [ ] All tests passing
- [ ] Code coverage >80% on business logic

### Documentation
- [x] README.md exists
- [x] API documentation (OpenAPI/Swagger)
- [x] Architecture documentation
- [x] Setup instructions
- [ ] Testing documentation
- [ ] Deployment guide

### Security
- [x] OAuth tokens encrypted
- [x] Input validation
- [x] Rate limiting
- [x] SQL injection prevention
- [x] No hardcoded secrets
- [x] Secrets in .env only

### Performance
- [x] N+1 queries fixed
- [x] Database indexes added
- [x] ML model caching (singleton pattern)
- [x] Vector store connection pooling

---

## Deployment Preparation

### Environment Configuration
- [ ] Create production .env template
- [ ] Document all required environment variables
- [ ] Set up secret management (e.g., Vault, AWS Secrets Manager)

### Database
- [ ] Run all Alembic migrations in test environment
- [ ] Verify migration rollback procedures
- [ ] Set up database backup strategy

### Monitoring
- [x] Health check endpoints
- [x] Structured logging
- [x] Request ID tracing
- [ ] Set up log aggregation (ELK, Datadog, etc.)
- [ ] Set up metrics (Prometheus)
- [ ] Set up alerting

### Infrastructure
- [ ] Create production docker-compose.yml
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure HTTPS/TLS
- [ ] Set up CDN for static assets
- [ ] Configure backup strategy

---

## Immediate Next Steps

1. **Fix Environment Issues**
   - Run tests in Docker: `docker-compose run --rm backend pytest tests/unit/ -v`
   - Or fix NixOS shell.nix with libstdc++.so.6

2. **Verify Existing Tests Pass**
   ```bash
   # Unit tests
   docker-compose run --rm backend pytest tests/unit/ -v

   # Integration tests
   docker-compose run --rm backend pytest tests/integration/ -v
   ```

3. **Create E2E Tests**
   - Focus on semantic search functionality
   - Test local file upload and processing
   - Test face detection workflow

4. **Run Pre-Commit Hooks**
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

5. **Final Verification**
   ```bash
   # All tests
   docker-compose run --rm backend pytest tests/ -v --cov=app

   # Pre-commit checks
   pre-commit run --all-files
   ```

6. **Push to GitHub**
   ```bash
   git remote add origin git@github.com:ottobunge/Photo-Explorer.git
   git push -u origin main
   ```

---

## Success Criteria for GitHub Push

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] E2E tests for core features passing
- [ ] Pre-commit hooks passing
- [ ] Code coverage >80%
- [ ] No secrets in repository
- [ ] Documentation complete
- [ ] Docker Compose builds successfully

---

## Notes

- NumPy/PyTorch environment issues are blocking test execution
- Consider running all tests in Docker containers to avoid environment issues
- E2E tests should use real services (PostgreSQL, Qdrant) with test data cleanup
- Pre-commit hooks configured but not tested yet

---

## Timeline

- **Now:** Fix environment and run existing tests
- **Next:** Create E2E tests for core features
- **Then:** Verify all tests pass
- **Finally:** Push to GitHub and set up CI/CD

---

## Resources

- [NumPy Troubleshooting](https://numpy.org/devdocs/user/troubleshooting-importerror.html)
- [NixOS Python Development](https://nixos.wiki/wiki/Python)
- [Docker Testing Best Practices](https://docs.docker.com/language/python/run-tests/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
