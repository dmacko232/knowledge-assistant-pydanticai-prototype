"""Tests for the SQL service."""

from services.sql_service import SQLService


class TestSQLServiceValidation:
    """Test query validation and safety checks."""

    def test_rejects_insert(self, sql_service: SQLService):
        result = sql_service.execute_query(
            "INSERT INTO kpi_catalog VALUES (99, 'x', 'x', 'x', 'x', 'x', 'x')"
        )
        assert "Error" in result

    def test_rejects_drop(self, sql_service: SQLService):
        result = sql_service.execute_query("DROP TABLE kpi_catalog")
        assert "Error" in result

    def test_rejects_update(self, sql_service: SQLService):
        result = sql_service.execute_query("UPDATE kpi_catalog SET definition='hacked'")
        assert "Error" in result

    def test_rejects_delete(self, sql_service: SQLService):
        result = sql_service.execute_query("DELETE FROM kpi_catalog")
        assert "Error" in result


class TestSQLServiceQueries:
    """Test valid SELECT queries."""

    def test_select_all_kpis(self, sql_service: SQLService):
        result = sql_service.execute_query("SELECT kpi_name, definition FROM kpi_catalog")
        assert "MRR" in result
        assert "Churn Rate" in result
        assert "NPS" in result

    def test_select_kpi_by_name(self, sql_service: SQLService):
        result = sql_service.execute_query(
            "SELECT kpi_name, owner_team FROM kpi_catalog WHERE kpi_name = 'MRR'"
        )
        assert "MRR" in result
        assert "Finance" in result

    def test_select_employees_by_team(self, sql_service: SQLService):
        result = sql_service.execute_query(
            "SELECT name, role FROM directory WHERE team = 'Engineering'"
        )
        assert "Alice Smith" in result
        assert "Carol Lee" in result

    def test_select_employee_by_email(self, sql_service: SQLService):
        result = sql_service.execute_query(
            "SELECT name, team FROM directory WHERE email = 'bob@northwind.com'"
        )
        assert "Bob Jones" in result
        assert "Finance" in result

    def test_no_results(self, sql_service: SQLService):
        result = sql_service.execute_query(
            "SELECT * FROM kpi_catalog WHERE kpi_name = 'nonexistent'"
        )
        assert result == "No results found."

    def test_sql_error_returns_message(self, sql_service: SQLService):
        result = sql_service.execute_query("SELECT * FROM nonexistent_table")
        assert "SQL Error" in result


class TestSQLServiceSchemas:
    """Test schema retrieval."""

    def test_get_schemas_contains_tables(self):
        schemas = SQLService.get_schemas()
        assert "kpi_catalog" in schemas
        assert "directory" in schemas
        assert "kpi_name" in schemas
        assert "email" in schemas
