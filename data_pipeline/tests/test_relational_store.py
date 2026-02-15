"""Unit tests for RelationalStore."""

import pytest

from database.models import Employee, KPICatalog
from database.relational_store import RelationalStore


class TestRelationalStore:
    """Test suite for RelationalStore."""

    @pytest.fixture
    def store(self, temp_db_path):
        """Create a RelationalStore instance."""
        store = RelationalStore(temp_db_path)
        store.connect()
        store.create_tables()
        yield store
        store.close()

    def test_connect_and_create_tables(self, temp_db_path):
        """Test database connection and table creation."""
        store = RelationalStore(temp_db_path)
        store.connect()

        assert store.engine is not None
        assert store.session is not None

        store.create_tables()
        store.close()

    def test_insert_and_query_kpi(self, store):
        """Test inserting and querying KPIs."""
        # Insert KPI
        kpi = KPICatalog(
            kpi_name="Test KPI",
            definition="Test definition",
            owner_team="Test Team",
            primary_source="test.table",
            last_updated="2026-01-01",
        )
        store.insert_kpis([kpi])

        # Query by name
        result = store.query_kpi_by_name("Test KPI")
        assert result is not None
        assert result.kpi_name == "Test KPI"
        assert result.definition == "Test definition"
        assert result.owner_team == "Test Team"

    def test_insert_and_query_employee(self, store):
        """Test inserting and querying employees."""
        # Insert employee
        employee = Employee(
            name="John Doe",
            email="john@example.com",
            team="Engineering",
            role="Developer",
            timezone="UTC",
        )
        store.insert_employees([employee])

        # Query by email
        result = store.query_employee_by_email("john@example.com")
        assert result is not None
        assert result.name == "John Doe"
        assert result.email == "john@example.com"
        assert result.team == "Engineering"

    def test_query_kpis_by_owner(self, store):
        """Test querying KPIs by owner team."""
        # Insert multiple KPIs
        kpis = [
            KPICatalog(
                kpi_name="KPI 1",
                definition="Definition 1",
                owner_team="Team A",
                primary_source="table1",
            ),
            KPICatalog(
                kpi_name="KPI 2",
                definition="Definition 2",
                owner_team="Team A",
                primary_source="table2",
            ),
            KPICatalog(
                kpi_name="KPI 3",
                definition="Definition 3",
                owner_team="Team B",
                primary_source="table3",
            ),
        ]
        store.insert_kpis(kpis)

        # Query by owner team
        team_a_kpis = store.query_kpis_by_owner("Team A")
        assert len(team_a_kpis) == 2
        assert all(kpi.owner_team == "Team A" for kpi in team_a_kpis)

    def test_query_employees_by_team(self, store):
        """Test querying employees by team."""
        # Insert multiple employees
        employees = [
            Employee(
                name="Alice",
                email="alice@example.com",
                team="Engineering",
                role="Developer",
                timezone="UTC",
            ),
            Employee(
                name="Bob",
                email="bob@example.com",
                team="Engineering",
                role="Developer",
                timezone="PST",
            ),
            Employee(
                name="Charlie",
                email="charlie@example.com",
                team="Sales",
                role="Manager",
                timezone="EST",
            ),
        ]
        store.insert_employees(employees)

        # Query by team
        eng_employees = store.query_employees_by_team("Engineering")
        assert len(eng_employees) == 2
        assert all(emp.team == "Engineering" for emp in eng_employees)

    def test_get_all_teams(self, store):
        """Test getting all unique teams."""
        # Insert employees from different teams
        employees = [
            Employee(
                name="Alice",
                email="alice@example.com",
                team="Engineering",
                role="Developer",
                timezone="UTC",
            ),
            Employee(
                name="Bob", email="bob@example.com", team="Sales", role="Manager", timezone="PST"
            ),
            Employee(
                name="Charlie",
                email="charlie@example.com",
                team="Marketing",
                role="Designer",
                timezone="EST",
            ),
        ]
        store.insert_employees(employees)

        # Get all teams
        teams = store.get_all_teams()
        assert len(teams) == 3
        assert "Engineering" in teams
        assert "Sales" in teams
        assert "Marketing" in teams

    def test_get_stats(self, store):
        """Test getting statistics."""
        # Insert data
        kpis = [
            KPICatalog(
                kpi_name="KPI 1",
                definition="Definition 1",
                owner_team="Team A",
                primary_source="table1",
            ),
            KPICatalog(
                kpi_name="KPI 2",
                definition="Definition 2",
                owner_team="Team B",
                primary_source="table2",
            ),
        ]
        store.insert_kpis(kpis)

        employees = [
            Employee(
                name="Alice",
                email="alice@example.com",
                team="Engineering",
                role="Developer",
                timezone="UTC",
            ),
            Employee(
                name="Bob", email="bob@example.com", team="Sales", role="Manager", timezone="PST"
            ),
        ]
        store.insert_employees(employees)

        # Get stats
        stats = store.get_stats()
        assert stats["total_kpis"] == 2
        assert stats["total_employees"] == 2
        assert "Team A" in stats["kpis_by_owner"]
        assert "Engineering" in stats["employees_by_team"]

    def test_upsert_kpi(self, store):
        """Test that inserting duplicate KPI updates the existing record."""
        # Insert KPI
        kpi1 = KPICatalog(
            kpi_name="Test KPI",
            definition="Original definition",
            owner_team="Team A",
            primary_source="table1",
        )
        store.insert_kpis([kpi1])

        # Insert same KPI with updated data
        kpi2 = KPICatalog(
            kpi_name="Test KPI",
            definition="Updated definition",
            owner_team="Team B",
            primary_source="table2",
        )
        store.insert_kpis([kpi2])

        # Should have only one KPI with updated data
        result = store.query_kpi_by_name("Test KPI")
        assert result.definition == "Updated definition"
        assert result.owner_team == "Team B"

    def test_upsert_employee(self, store):
        """Test that inserting duplicate employee updates the existing record."""
        # Insert employee
        emp1 = Employee(
            name="John Doe",
            email="john@example.com",
            team="Engineering",
            role="Developer",
            timezone="UTC",
        )
        store.insert_employees([emp1])

        # Insert same employee with updated data
        emp2 = Employee(
            name="John Smith",
            email="john@example.com",
            team="Sales",
            role="Manager",
            timezone="PST",
        )
        store.insert_employees([emp2])

        # Should have only one employee with updated data
        result = store.query_employee_by_email("john@example.com")
        assert result.name == "John Smith"
        assert result.team == "Sales"

    def test_reset(self, store):
        """Test resetting the database."""
        # Insert data
        kpi = KPICatalog(
            kpi_name="Test KPI",
            definition="Test definition",
            owner_team="Test Team",
            primary_source="test.table",
        )
        store.insert_kpis([kpi])

        # Reset
        store.reset()

        # Recreate tables
        store.create_tables()

        # Verify data is gone
        result = store.query_kpi_by_name("Test KPI")
        assert result is None
