"""Relational storage for KPIs and employee directory."""

from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from database.interfaces import RelationalStoreInterface
from database.models import Employee, KPICatalog


class RelationalStore(RelationalStoreInterface):
    """Manages relational tables (KPI catalog, employee directory)."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.engine = None
        self.session: Session | None = None

    def connect(self) -> None:
        """Connect to database."""
        connection_string = f"sqlite:///{self.db_path}"
        self.engine = create_engine(connection_string, echo=False)
        self.session = Session(self.engine)

    def close(self) -> None:
        """Close database connection."""
        if self.session:
            self.session.close()

    def create_tables(self) -> None:
        """Create KPI and directory tables."""
        if not self.engine:
            raise RuntimeError("Database not connected. Call connect() first.")
        SQLModel.metadata.create_all(
            self.engine,
            tables=[KPICatalog.__table__, Employee.__table__],
        )

    def insert_kpis(self, kpis: list[KPICatalog]) -> None:
        """Insert or update KPIs (upsert by kpi_name)."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        for kpi in kpis:
            existing = self.session.exec(
                select(KPICatalog).where(KPICatalog.kpi_name == kpi.kpi_name)
            ).first()
            if existing:
                existing.definition = kpi.definition
                existing.owner_team = kpi.owner_team
                existing.primary_source = kpi.primary_source
                existing.last_updated = kpi.last_updated
                self.session.add(existing)
            else:
                self.session.add(kpi)
        self.session.commit()

    def insert_employees(self, employees: list[Employee]) -> None:
        """Insert or update employees (upsert by email)."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        for emp in employees:
            existing = self.session.exec(
                select(Employee).where(Employee.email == emp.email)
            ).first()
            if existing:
                existing.name = emp.name
                existing.team = emp.team
                existing.role = emp.role
                existing.timezone = emp.timezone
                self.session.add(existing)
            else:
                self.session.add(emp)
        self.session.commit()

    def query_kpi_by_name(self, name: str) -> KPICatalog | None:
        """Get KPI by name."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.session.exec(select(KPICatalog).where(KPICatalog.kpi_name == name)).first()

    def query_employee_by_email(self, email: str) -> Employee | None:
        """Get employee by email."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.session.exec(select(Employee).where(Employee.email == email)).first()

    def query_kpis_by_owner(self, owner_team: str) -> list[KPICatalog]:
        """Get all KPIs for an owner team."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        return list(
            self.session.exec(select(KPICatalog).where(KPICatalog.owner_team == owner_team)).all()
        )

    def query_employees_by_team(self, team: str) -> list[Employee]:
        """Get all employees in a team."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        return list(self.session.exec(select(Employee).where(Employee.team == team)).all())

    def get_all_teams(self) -> list[str]:
        """Get distinct team names from directory."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        employees = self.session.exec(select(Employee)).all()
        return sorted({e.team for e in employees})

    def get_stats(self) -> dict:
        """Get counts and breakdowns."""
        if not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        kpis = list(self.session.exec(select(KPICatalog)).all())
        employees = list(self.session.exec(select(Employee)).all())
        kpis_by_owner: dict[str, int] = {}
        for k in kpis:
            kpis_by_owner[k.owner_team] = kpis_by_owner.get(k.owner_team, 0) + 1
        employees_by_team: dict[str, int] = {}
        for e in employees:
            employees_by_team[e.team] = employees_by_team.get(e.team, 0) + 1
        return {
            "total_kpis": len(kpis),
            "total_employees": len(employees),
            "kpis_by_owner": kpis_by_owner,
            "employees_by_team": employees_by_team,
        }

    def reset(self) -> None:
        """Drop KPI and directory tables."""
        if not self.engine or not self.session:
            raise RuntimeError("Database not connected. Call connect() first.")
        SQLModel.metadata.drop_all(
            self.engine,
            tables=[KPICatalog.__table__, Employee.__table__],
        )
        self.session.commit()
