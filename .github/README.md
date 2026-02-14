# CI/CD Configuration

This directory contains GitHub Actions workflows and configurations for the repository.

## Workflows

### Main CI Workflow ([ci.yml](workflows/ci.yml))
- Orchestrates all component workflows
- Runs on push to `main`, `develop`, and `feat/*` branches
- Requires all component checks to pass

### Component Workflows

1. **[data-analysis.yml](workflows/data-analysis.yml)** - Data Analysis CI
   - Runs ruff linter and formatter
   - Type checking with mypy
   - Executes analysis script
   - Uploads analysis reports as artifacts

2. **[backend.yml](workflows/backend.yml)** - Backend CI
   - Multi-version Python testing (3.11, 3.12, 3.13)
   - Ruff linting and formatting
   - Type checking with mypy
   - Pytest with coverage
   - Uploads coverage to Codecov

3. **[data-pipeline.yml](workflows/data-pipeline.yml)** - Data Pipeline CI
   - Multi-version Python testing (3.11, 3.12, 3.13)
   - Ruff linting and formatting
   - Type checking with mypy
   - Pytest with coverage
   - Uploads coverage to Codecov

4. **[frontend.yml](workflows/frontend.yml)** - Frontend CI
   - ESLint linting
   - Prettier formatting check
   - TypeScript type checking
   - Vitest testing with coverage
   - Build verification
   - Uploads build artifacts

## Dependabot

[dependabot.yml](dependabot.yml) configures automated dependency updates for:
- GitHub Actions
- Frontend npm packages
- Python packages for all Python components

Updates are checked weekly and create PRs with appropriate labels.

## Path-based Triggers

Each workflow only runs when files in its respective component directory change, reducing unnecessary CI runs:

```yaml
paths:
  - 'component_name/**'
  - '.github/workflows/component_name.yml'
```

## Artifacts

- **Data Analysis Reports**: Generated markdown reports (30 days retention)
- **Frontend Build**: Production build artifacts (7 days retention)
- **Coverage Reports**: Uploaded to Codecov for tracking

## Local Testing

Run CI checks locally before pushing:

```bash
# Run all checks
make ci

# Or individually
make lint
make format
make type-check
make test
```
