"""Processing for structured data (CSV, JSON)."""

import csv
import json

import config
from database.models import Employee, KPICatalog


class StructuredDataProcessor:
    """Processes structured data files (KPI catalog, employee directory)."""

    def __init__(self):
        """Initialize structured data processor."""
        self.kpi_file = config.STRUCTURED_DATA_DIR / "kpi_catalog.csv"
        self.directory_file = config.STRUCTURED_DATA_DIR / "directory.json"

    def process_kpi_catalog(self) -> list[KPICatalog]:
        """
        Process KPI catalog from CSV.

        Returns:
            List of KPICatalog model instances
        """
        if not self.kpi_file.exists():
            raise FileNotFoundError(f"KPI catalog not found: {self.kpi_file}")

        kpis = []
        with open(self.kpi_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                kpi = KPICatalog(
                    kpi_name=row["kpi_name"].strip(),
                    definition=row["definition"].strip(),
                    owner_team=row["owner_team"].strip(),
                    primary_source=row["primary_source"].strip(),
                    last_updated=row.get("last_updated", "").strip() or None,
                )
                kpis.append(kpi)

        print(f"✓ Processed {len(kpis)} KPIs from {self.kpi_file.name}")
        return kpis

    def process_directory(self) -> list[Employee]:
        """
        Process employee directory from JSON.

        Returns:
            List of Employee model instances
        """
        if not self.directory_file.exists():
            raise FileNotFoundError(f"Directory not found: {self.directory_file}")

        with open(self.directory_file, encoding="utf-8") as f:
            employee_data = json.load(f)

        # Create Employee instances
        employees = []
        for emp_dict in employee_data:
            employee = Employee(
                name=emp_dict["name"].strip(),
                email=emp_dict["email"].strip(),
                team=emp_dict["team"].strip(),
                role=emp_dict["role"].strip(),
                timezone=emp_dict["timezone"].strip(),
            )
            employees.append(employee)

        print(f"✓ Processed {len(employees)} employees from {self.directory_file.name}")
        return employees

    def validate_kpi_data(self, kpis: list[KPICatalog]) -> bool:
        """
        Validate KPI data completeness.

        Args:
            kpis: List of KPICatalog model instances

        Returns:
            True if validation passes
        """
        required_fields = ["kpi_name", "definition", "owner_team", "primary_source"]

        issues = []
        for i, kpi in enumerate(kpis):
            for field in required_fields:
                value = getattr(kpi, field, None)
                if not value:
                    issues.append(f"KPI {i + 1}: Missing {field}")

        if issues:
            print("⚠ KPI validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("✓ KPI data validation passed")
        return True

    def validate_directory_data(self, employees: list[Employee]) -> bool:
        """
        Validate employee directory data completeness.

        Args:
            employees: List of Employee model instances

        Returns:
            True if validation passes
        """
        required_fields = ["name", "email", "team", "role", "timezone"]

        issues = []
        emails = set()

        for i, emp in enumerate(employees):
            # Check required fields
            for field in required_fields:
                value = getattr(emp, field, None)
                if not value:
                    issues.append(f"Employee {i + 1}: Missing {field}")

            # Check for duplicate emails
            if emp.email in emails:
                issues.append(f"Employee {i + 1}: Duplicate email {emp.email}")
            emails.add(emp.email)

        if issues:
            print("⚠ Directory validation issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False

        print("✓ Directory data validation passed")
        return True


if __name__ == "__main__":
    # Test structured data processor
    processor = StructuredDataProcessor()

    try:
        # Test KPI processing
        print("Testing KPI catalog processing...")
        kpis = processor.process_kpi_catalog()
        processor.validate_kpi_data(kpis)
        print(f"  Sample KPI: {kpis[0].kpi_name}")

        # Test directory processing
        print("\nTesting directory processing...")
        employees = processor.process_directory()
        processor.validate_directory_data(employees)
        print(f"  Sample employee: {employees[0].name}")

        print("\n✓ Structured data processor test complete")

    except FileNotFoundError as e:
        print(f"⚠ {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
