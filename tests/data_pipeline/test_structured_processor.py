"""Unit tests for StructuredDataProcessor."""

import csv
import json

import pytest

from database.models import Employee, KPICatalog
from processors.structured_processor import StructuredDataProcessor


class TestStructuredDataProcessor:
    """Test suite for StructuredDataProcessor."""

    @pytest.fixture
    def processor(self, temp_dir, monkeypatch):
        """Create a StructuredDataProcessor with test files."""
        # Create test CSV file
        kpi_file = temp_dir / "kpi_catalog.csv"
        with open(kpi_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "kpi_name",
                    "definition",
                    "owner_team",
                    "primary_source",
                    "last_updated",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "kpi_name": "Revenue",
                    "definition": "Total revenue for the period",
                    "owner_team": "Finance",
                    "primary_source": "finance.revenue",
                    "last_updated": "2026-01-01",
                }
            )
            writer.writerow(
                {
                    "kpi_name": "Active Users",
                    "definition": "Number of active users",
                    "owner_team": "Product",
                    "primary_source": "analytics.users",
                    "last_updated": "2026-01-15",
                }
            )

        # Create test JSON file
        directory_file = temp_dir / "directory.json"
        with open(directory_file, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "name": "Alice Johnson",
                        "email": "alice@example.com",
                        "team": "Engineering",
                        "role": "Developer",
                        "timezone": "UTC",
                    },
                    {
                        "name": "Bob Smith",
                        "email": "bob@example.com",
                        "team": "Product",
                        "role": "Manager",
                        "timezone": "PST",
                    },
                ],
                f,
            )

        # Monkey patch config
        import config

        monkeypatch.setattr(config, "STRUCTURED_DATA_DIR", temp_dir)

        processor = StructuredDataProcessor()
        return processor

    def test_process_kpi_catalog(self, processor):
        """Test processing KPI catalog from CSV."""
        kpis = processor.process_kpi_catalog()

        assert len(kpis) == 2
        assert all(isinstance(kpi, KPICatalog) for kpi in kpis)

        # Check first KPI
        kpi1 = kpis[0]
        assert kpi1.kpi_name == "Revenue"
        assert kpi1.definition == "Total revenue for the period"
        assert kpi1.owner_team == "Finance"
        assert kpi1.primary_source == "finance.revenue"
        assert kpi1.last_updated == "2026-01-01"

        # Check second KPI
        kpi2 = kpis[1]
        assert kpi2.kpi_name == "Active Users"
        assert kpi2.owner_team == "Product"

    def test_process_directory(self, processor):
        """Test processing employee directory from JSON."""
        employees = processor.process_directory()

        assert len(employees) == 2
        assert all(isinstance(emp, Employee) for emp in employees)

        # Check first employee
        emp1 = employees[0]
        assert emp1.name == "Alice Johnson"
        assert emp1.email == "alice@example.com"
        assert emp1.team == "Engineering"
        assert emp1.role == "Developer"
        assert emp1.timezone == "UTC"

        # Check second employee
        emp2 = employees[1]
        assert emp2.name == "Bob Smith"
        assert emp2.team == "Product"

    def test_validate_kpi_data_valid(self, processor):
        """Test validation passes for valid KPI data."""
        kpis = [
            KPICatalog(
                kpi_name="Test KPI",
                definition="Test definition",
                owner_team="Test Team",
                primary_source="test.table",
            )
        ]

        assert processor.validate_kpi_data(kpis) is True

    def test_validate_kpi_data_invalid(self, processor):
        """Test validation fails for invalid KPI data."""
        kpis = [
            KPICatalog(
                kpi_name="",  # Empty name
                definition="Test definition",
                owner_team="Test Team",
                primary_source="test.table",
            )
        ]

        assert processor.validate_kpi_data(kpis) is False

    def test_validate_directory_data_valid(self, processor):
        """Test validation passes for valid employee data."""
        employees = [
            Employee(
                name="John Doe",
                email="john@example.com",
                team="Engineering",
                role="Developer",
                timezone="UTC",
            )
        ]

        assert processor.validate_directory_data(employees) is True

    def test_validate_directory_data_missing_field(self, processor):
        """Test validation fails for missing required field."""
        employees = [
            Employee(
                name="John Doe",
                email="",  # Empty email
                team="Engineering",
                role="Developer",
                timezone="UTC",
            )
        ]

        assert processor.validate_directory_data(employees) is False

    def test_validate_directory_data_duplicate_email(self, processor):
        """Test validation fails for duplicate emails."""
        employees = [
            Employee(
                name="John Doe",
                email="john@example.com",
                team="Engineering",
                role="Developer",
                timezone="UTC",
            ),
            Employee(
                name="Jane Doe",
                email="john@example.com",  # Duplicate email
                team="Marketing",
                role="Designer",
                timezone="PST",
            ),
        ]

        assert processor.validate_directory_data(employees) is False

    def test_process_kpi_catalog_file_not_found(self, temp_dir, monkeypatch):
        """Test that FileNotFoundError is raised when KPI file doesn't exist."""
        import config

        monkeypatch.setattr(config, "STRUCTURED_DATA_DIR", temp_dir / "nonexistent")

        processor = StructuredDataProcessor()

        with pytest.raises(FileNotFoundError, match="KPI catalog not found"):
            processor.process_kpi_catalog()

    def test_process_directory_file_not_found(self, temp_dir, monkeypatch):
        """Test that FileNotFoundError is raised when directory file doesn't exist."""
        import config

        monkeypatch.setattr(config, "STRUCTURED_DATA_DIR", temp_dir / "nonexistent")

        processor = StructuredDataProcessor()

        with pytest.raises(FileNotFoundError, match="Directory not found"):
            processor.process_directory()

    def test_process_kpi_with_whitespace(self, temp_dir, monkeypatch):
        """Test that whitespace is trimmed from KPI data."""
        # Create CSV with whitespace
        kpi_file = temp_dir / "kpi_catalog.csv"
        with open(kpi_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "kpi_name",
                    "definition",
                    "owner_team",
                    "primary_source",
                    "last_updated",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "kpi_name": "  Revenue  ",
                    "definition": "  Total revenue  ",
                    "owner_team": "  Finance  ",
                    "primary_source": "  finance.revenue  ",
                    "last_updated": "",
                }
            )

        # Mock directory file
        directory_file = temp_dir / "directory.json"
        with open(directory_file, "w") as f:
            json.dump([], f)

        import config

        monkeypatch.setattr(config, "STRUCTURED_DATA_DIR", temp_dir)

        processor = StructuredDataProcessor()
        kpis = processor.process_kpi_catalog()

        assert kpis[0].kpi_name == "Revenue"
        assert kpis[0].definition == "Total revenue"
        assert kpis[0].owner_team == "Finance"
        assert kpis[0].primary_source == "finance.revenue"
        assert kpis[0].last_updated is None  # Empty string should be None
