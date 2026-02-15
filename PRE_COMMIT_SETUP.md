# Pre-commit Hooks Setup

## ✅ Installation Complete

Pre-commit hooks have been successfully installed and configured!

## What Got Installed

### Pre-commit Hooks
Installed at: `.git/hooks/pre-commit`

The following checks run automatically on every commit:

1. **Basic Checks**
   - Trim trailing whitespace
   - Fix end of files (ensure newline at EOF)
   - Check YAML syntax
   - Check JSON syntax
   - Check TOML syntax
   - Check for large files (>1MB)
   - Check for merge conflicts
   - Fix mixed line endings (LF)

2. **Python Checks** (backend, data_analysis, data_pipeline)
   - **Ruff linter** - Auto-fix style issues
   - **Ruff formatter** - Auto-format code
   - **mypy** - Type checking (on modified files)

3. **Frontend Checks**
   - **Prettier** - Auto-format JS/TS/JSON/CSS/MD
   - **ESLint** - Lint TypeScript/JavaScript (on modified files)

## Usage

### Automatic (Recommended)
Pre-commit hooks run automatically when you commit:

```bash
git add .
git commit -m "Your message"
# Pre-commit hooks run automatically!
```

If hooks fail:
- They'll auto-fix what they can
- You'll need to `git add` the fixed files
- Then commit again

### Manual Run

Run on all files:
```bash
pre-commit run --all-files
```

Run on specific files:
```bash
pre-commit run --files path/to/file.py
```

Run specific hook:
```bash
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

### Skip Hooks (Use Sparingly!)

If you absolutely need to skip pre-commit hooks:
```bash
git commit -m "Message" --no-verify
```

⚠️ **Warning**: Only use `--no-verify` when absolutely necessary!

## Configuration

Config file: `.pre-commit-config.yaml`

### Update Hooks

Update to latest versions:
```bash
pre-commit autoupdate
```

### Disable Specific Hooks

Edit `.pre-commit-config.yaml` and comment out unwanted hooks.

## Integration with CI/CD

Pre-commit hooks match the CI/CD checks, so if pre-commit passes locally, CI should pass too!

| Check | Pre-commit | CI/CD |
|-------|-----------|-------|
| Ruff lint | ✅ | ✅ |
| Ruff format | ✅ | ✅ |
| mypy | ✅ | ✅ |
| ty | ❌ | ✅ |
| ESLint | ✅ | ✅ |
| Prettier | ✅ | ✅ |
| Tests | ❌ | ✅ |

*Note: Tests and ty are only run in CI, not in pre-commit (to keep commits fast).*

## Troubleshooting

### Hooks are slow
Pre-commit caches environments, so the first run is slow but subsequent runs are fast.

### Hook failed but I fixed it
```bash
git add .
git commit -m "Message"
# Hooks will run again on the fixed files
```

### Want to bypass for a quick fix
```bash
git commit -m "WIP: quick fix" --no-verify
```
Then fix and recommit properly later.

### Update hook versions
```bash
pre-commit autoupdate
pre-commit run --all-files  # Test updated hooks
```

## Benefits

✅ **Catch issues early** - Before pushing to CI
✅ **Consistent code style** - Auto-formatted on commit
✅ **Faster feedback** - No waiting for CI
✅ **Team alignment** - Everyone uses same checks
✅ **CI cost savings** - Fewer failed CI runs

## Status

**Current Status**: ✅ All checks passing

Run `pre-commit run --all-files` to verify anytime!
