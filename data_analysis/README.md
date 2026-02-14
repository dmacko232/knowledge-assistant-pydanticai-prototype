# Data Analysis

This directory contains data analysis scripts for the Northwind Commerce knowledge base.

## Setup

This project uses `uv` for Python environment and dependency management.

```bash
# Create virtual environment and install dependencies
uv sync

# Run analysis
uv run python analyze.py
```

## Structure

- `analyze.py` - Main analysis script
- `outputs/` - Generated analysis reports (markdown files)
- `pyproject.toml` - Project configuration

## Analysis Reports

The script generates the following reports in `outputs/`:

1. **overview.md** - High-level summary of all data
2. **team_analysis.md** - Team composition and ownership breakdown
3. **kpi_analysis.md** - Detailed KPI metrics and ownership
4. **document_metadata.md** - Document metadata and statistics
5. **policy_compliance.md** - Policy documents and freshness analysis
6. **data_quality.md** - Data completeness and consistency checks

## Data Sources

The analysis reads from:
- `../data/raw/structured/directory.json` - Employee directory
- `../data/raw/structured/kpi_catalog.csv` - KPI definitions
- `../data/raw/documents/` - All markdown documentation files