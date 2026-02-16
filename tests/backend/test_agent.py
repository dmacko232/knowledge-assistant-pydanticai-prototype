"""Tests for the agent module."""

from application.infrastructure.agent import SYSTEM_PROMPT, AgentDeps


class TestSystemPrompt:
    """Verify the system prompt contains required behavioural rules."""

    def test_contains_grounding_rule(self):
        assert "MUST ground ALL answers" in SYSTEM_PROMPT

    def test_contains_unknown_response(self):
        assert "I can't find this in the knowledge base" in SYSTEM_PROMPT

    def test_contains_citation_instruction(self):
        assert "[1]" in SYSTEM_PROMPT
        assert "[2]" in SYSTEM_PROMPT
        assert "Sources" in SYSTEM_PROMPT

    def test_contains_recency_instruction(self):
        assert "last_updated" in SYSTEM_PROMPT
        assert "MORE RECENT" in SYSTEM_PROMPT

    def test_contains_security_instruction(self):
        assert "NEVER reveal" in SYSTEM_PROMPT
        assert "system prompt" in SYSTEM_PROMPT

    def test_contains_table_schemas(self):
        assert "kpi_catalog" in SYSTEM_PROMPT
        assert "directory" in SYSTEM_PROMPT
        assert "kpi_name" in SYSTEM_PROMPT
        assert "email" in SYSTEM_PROMPT

    def test_contains_tool_usage_instructions(self):
        assert "search_knowledge_base" in SYSTEM_PROMPT
        assert "lookup_structured_data" in SYSTEM_PROMPT
        assert "standalone" in SYSTEM_PROMPT


class TestAgentDeps:
    """Test the AgentDeps dataclass."""

    def test_can_create(self):
        deps = AgentDeps(retrieval_service=None, sql_service=None)  # type: ignore[arg-type]
        assert deps.retrieval_service is None
        assert deps.sql_service is None
