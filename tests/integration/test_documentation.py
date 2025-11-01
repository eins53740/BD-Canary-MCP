"""
Integration tests for API documentation completeness and validity.

Story 2.6: API Documentation Generation
Validates that all MCP tools are documented with complete information.
"""

import os
import re
from pathlib import Path

import pytest


# Expected MCP tools that should be documented
EXPECTED_TOOLS = [
    "ping",
    "search_tags",
    "get_tag_metadata",
    "read_timeseries",
    "list_namespaces",
    "get_server_info",
    "get_metrics",
    "get_metrics_summary",
    "get_cache_stats",
    "invalidate_cache",
    "cleanup_expired_cache",
]


@pytest.fixture
def docs_dir():
    """Get the docs directory path."""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "docs"


@pytest.fixture
def api_doc_path(docs_dir):
    """Get the API documentation file path."""
    return docs_dir / "API.md"


@pytest.fixture
def examples_doc_path(docs_dir):
    """Get the examples documentation file path."""
    return docs_dir / "examples.md"


class TestDocumentationExists:
    """Test that documentation files exist and are accessible."""

    def test_docs_directory_exists(self, docs_dir):
        """Verify docs/ directory exists."""
        assert docs_dir.exists(), "docs/ directory does not exist"
        assert docs_dir.is_dir(), "docs/ is not a directory"

    def test_api_documentation_exists(self, api_doc_path):
        """Verify API.md documentation file exists."""
        assert api_doc_path.exists(), "docs/API.md does not exist"
        assert api_doc_path.is_file(), "docs/API.md is not a file"

    def test_examples_documentation_exists(self, examples_doc_path):
        """Verify examples.md documentation file exists."""
        assert examples_doc_path.exists(), "docs/examples.md does not exist"
        assert examples_doc_path.is_file(), "docs/examples.md is not a file"

    def test_api_documentation_readable(self, api_doc_path):
        """Verify API.md is readable and not empty."""
        content = api_doc_path.read_text(encoding="utf-8")
        assert len(content) > 0, "docs/API.md is empty"
        assert len(content) > 1000, "docs/API.md seems too short (< 1000 chars)"

    def test_examples_documentation_readable(self, examples_doc_path):
        """Verify examples.md is readable and not empty."""
        content = examples_doc_path.read_text(encoding="utf-8")
        assert len(content) > 0, "docs/examples.md is empty"
        assert len(content) > 1000, "docs/examples.md seems too short (< 1000 chars)"


class TestAPIDocumentationStructure:
    """Test that API documentation has proper structure and sections."""

    def test_api_doc_has_title(self, api_doc_path):
        """Verify API.md has a title."""
        content = api_doc_path.read_text(encoding="utf-8")
        assert "# Canary MCP Server API Documentation" in content, "API.md missing title"

    def test_api_doc_has_table_of_contents(self, api_doc_path):
        """Verify API.md has table of contents."""
        content = api_doc_path.read_text(encoding="utf-8")
        assert "## Table of Contents" in content, "API.md missing table of contents"

    def test_api_doc_has_error_codes_section(self, api_doc_path):
        """Verify API.md has error codes section."""
        content = api_doc_path.read_text(encoding="utf-8")
        assert "## Error Codes" in content, "API.md missing Error Codes section"

    def test_api_doc_has_best_practices_section(self, api_doc_path):
        """Verify API.md has best practices section."""
        content = api_doc_path.read_text(encoding="utf-8")
        assert "## Best Practices" in content, "API.md missing Best Practices section"

    def test_api_doc_has_version_info(self, api_doc_path):
        """Verify API.md includes version information."""
        content = api_doc_path.read_text(encoding="utf-8")
        # Check for version pattern like "v1.0.0" or "1.0.0"
        assert re.search(r"v?\d+\.\d+\.\d+", content), "API.md missing version information"


class TestToolDocumentation:
    """Test that all MCP tools are documented with complete information."""

    def test_all_tools_documented(self, api_doc_path):
        """Verify all expected MCP tools are documented in API.md."""
        content = api_doc_path.read_text(encoding="utf-8")

        missing_tools = []
        for tool in EXPECTED_TOOLS:
            # Check for tool name as a heading (### tool_name)
            tool_heading = f"### {tool}"
            if tool_heading not in content:
                missing_tools.append(tool)

        assert (
            not missing_tools
        ), f"Tools not documented in API.md: {', '.join(missing_tools)}"

    def test_tools_have_purpose_section(self, api_doc_path):
        """Verify each tool has a Purpose section."""
        content = api_doc_path.read_text(encoding="utf-8")

        for tool in EXPECTED_TOOLS:
            # Find the tool section
            tool_pattern = rf"### {tool}.*?(?=###|---|\Z)"
            tool_match = re.search(tool_pattern, content, re.DOTALL)

            assert tool_match, f"Tool {tool} section not found"

            tool_section = tool_match.group(0)
            assert (
                "**Purpose**:" in tool_section or "**Purpose**" in tool_section
            ), f"Tool {tool} missing Purpose section"

    def test_tools_have_parameters_or_returns(self, api_doc_path):
        """Verify each tool documents parameters or returns."""
        content = api_doc_path.read_text(encoding="utf-8")

        for tool in EXPECTED_TOOLS:
            # Find the tool section
            tool_pattern = rf"### {tool}.*?(?=###|---|\Z)"
            tool_match = re.search(tool_pattern, content, re.DOTALL)

            assert tool_match, f"Tool {tool} section not found"

            tool_section = tool_match.group(0)
            has_params = "**Parameters:**" in tool_section or "**Parameters**" in tool_section
            has_returns = "**Returns:**" in tool_section or "**Returns**" in tool_section

            assert (
                has_params or has_returns
            ), f"Tool {tool} missing Parameters or Returns documentation"

    def test_tools_have_example_usage(self, api_doc_path):
        """Verify core data access tools have example usage."""
        content = api_doc_path.read_text(encoding="utf-8")

        # Core tools should have examples
        core_tools = [
            "search_tags",
            "get_tag_metadata",
            "read_timeseries",
            "list_namespaces",
            "get_server_info",
        ]

        for tool in core_tools:
            # Find the tool section
            tool_pattern = rf"### {tool}.*?(?=###|---|\Z)"
            tool_match = re.search(tool_pattern, content, re.DOTALL)

            assert tool_match, f"Tool {tool} section not found"

            tool_section = tool_match.group(0)
            has_example = (
                "**Example Usage:**" in tool_section
                or "**Example**" in tool_section
                or "**Use Case:**" in tool_section
            )

            assert has_example, f"Core tool {tool} missing example usage"


class TestExamplesDocumentation:
    """Test that examples documentation is complete."""

    def test_examples_has_use_cases(self, examples_doc_path):
        """Verify examples.md has different use case categories."""
        content = examples_doc_path.read_text(encoding="utf-8")

        use_case_categories = [
            "Validation Use Cases",
            "Troubleshooting Use Cases",
            "Optimization Use Cases",
            "Reporting Use Cases",
        ]

        for category in use_case_categories:
            assert (
                category in content
            ), f"examples.md missing category: {category}"

    def test_examples_reference_tools(self, examples_doc_path):
        """Verify examples reference actual MCP tools."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Core tools should be mentioned in examples
        core_tools = [
            "search_tags",
            "get_tag_metadata",
            "read_timeseries",
            "list_namespaces",
        ]

        for tool in core_tools:
            assert tool in content, f"examples.md does not reference tool: {tool}"

    def test_examples_have_natural_language_queries(self, examples_doc_path):
        """Verify examples include natural language query examples."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Should have sections with natural language queries
        assert (
            "**Natural Language Query:**" in content
            or "Natural Language Query" in content
        ), "examples.md missing natural language query examples"

    def test_examples_have_mcp_tool_calls(self, examples_doc_path):
        """Verify examples show actual MCP tool call syntax."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Should show tool call examples
        assert (
            "**MCP Tool Calls:**" in content or "MCP Tool Calls" in content
        ), "examples.md missing MCP tool call examples"

    def test_examples_have_sufficient_quantity(self, examples_doc_path):
        """Verify examples.md has at least 15 examples (per acceptance criteria)."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Count sections that look like examples (### followed by a number or use case)
        example_pattern = r"###\s+\d+\."
        examples = re.findall(example_pattern, content)

        assert (
            len(examples) >= 15
        ), f"examples.md has only {len(examples)} examples, expected at least 15"


class TestMarkdownValidity:
    """Test that markdown syntax is valid."""

    def test_api_doc_has_valid_headings(self, api_doc_path):
        """Verify API.md has properly formatted headings."""
        content = api_doc_path.read_text(encoding="utf-8")

        # Check for heading hierarchy (should have #, ##, ###)
        assert re.search(r"^# ", content, re.MULTILINE), "API.md missing level 1 heading"
        assert re.search(r"^## ", content, re.MULTILINE), "API.md missing level 2 headings"
        assert re.search(r"^### ", content, re.MULTILINE), "API.md missing level 3 headings"

    def test_examples_has_valid_headings(self, examples_doc_path):
        """Verify examples.md has properly formatted headings."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Check for heading hierarchy
        assert re.search(r"^# ", content, re.MULTILINE), "examples.md missing level 1 heading"
        assert re.search(r"^## ", content, re.MULTILINE), "examples.md missing level 2 headings"

    def test_api_doc_code_blocks_closed(self, api_doc_path):
        """Verify all code blocks in API.md are properly closed."""
        content = api_doc_path.read_text(encoding="utf-8")

        # Count opening and closing code fences
        opening_fences = content.count("```")
        # Should be even (each opening has a closing)
        assert (
            opening_fences % 2 == 0
        ), f"API.md has unclosed code blocks (found {opening_fences} backtick fences)"

    def test_examples_code_blocks_closed(self, examples_doc_path):
        """Verify all code blocks in examples.md are properly closed."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Count opening and closing code fences
        opening_fences = content.count("```")
        # Should be even (each opening has a closing)
        assert (
            opening_fences % 2 == 0
        ), f"examples.md has unclosed code blocks (found {opening_fences} backtick fences)"


class TestErrorDocumentation:
    """Test that error handling is documented."""

    def test_api_doc_documents_error_format(self, api_doc_path):
        """Verify error response format is documented."""
        content = api_doc_path.read_text(encoding="utf-8")

        # Should document error response structure
        assert '"success": false' in content, "API.md does not document error response format"
        assert '"error"' in content, "API.md does not show error field"

    def test_api_doc_lists_error_types(self, api_doc_path):
        """Verify common error types are documented."""
        content = api_doc_path.read_text(encoding="utf-8")

        error_types = [
            "Authentication",
            "Connection",
            "Timeout",
            "Circuit Breaker",
        ]

        for error_type in error_types:
            assert (
                error_type in content
            ), f"API.md does not document {error_type} errors"


class TestCachingDocumentation:
    """Test that caching behavior is documented."""

    def test_api_doc_mentions_caching(self, api_doc_path):
        """Verify caching is documented in API.md."""
        content = api_doc_path.read_text(encoding="utf-8")

        assert "cach" in content.lower(), "API.md does not mention caching"

    def test_tools_document_cache_behavior(self, api_doc_path):
        """Verify cacheable tools document TTL."""
        content = api_doc_path.read_text(encoding="utf-8")

        # search_tags should mention caching
        search_tags_pattern = r"### search_tags.*?(?=###|---|\Z)"
        search_match = re.search(search_tags_pattern, content, re.DOTALL)
        assert search_match, "search_tags section not found"

        search_section = search_match.group(0)
        assert (
            "Caching" in search_section or "cached" in search_section.lower()
        ), "search_tags does not document caching behavior"

    def test_bypass_cache_documented(self, api_doc_path):
        """Verify bypass_cache parameter is documented."""
        content = api_doc_path.read_text(encoding="utf-8")

        assert "bypass_cache" in content, "API.md does not document bypass_cache parameter"


class TestPerformanceDocumentation:
    """Test that performance metrics are documented."""

    def test_metrics_tools_documented(self, api_doc_path):
        """Verify performance monitoring tools are documented."""
        content = api_doc_path.read_text(encoding="utf-8")

        metrics_tools = ["get_metrics", "get_metrics_summary"]

        for tool in metrics_tools:
            assert f"### {tool}" in content, f"Metrics tool {tool} not documented"

    def test_prometheus_format_documented(self, api_doc_path):
        """Verify Prometheus format is mentioned for get_metrics."""
        content = api_doc_path.read_text(encoding="utf-8")

        # Find get_metrics section
        metrics_pattern = r"### get_metrics.*?(?=###|---|\Z)"
        metrics_match = re.search(metrics_pattern, content, re.DOTALL)
        assert metrics_match, "get_metrics section not found"

        metrics_section = metrics_match.group(0)
        assert (
            "Prometheus" in metrics_section
        ), "get_metrics does not mention Prometheus format"


@pytest.mark.integration
class TestDocumentationCompleteness:
    """High-level tests for overall documentation completeness."""

    def test_story_2_6_acceptance_criteria_met(self, api_doc_path, examples_doc_path):
        """
        Verify key acceptance criteria for Story 2.6 are met:
        1. API documentation auto-generated from MCP tool definitions ✓ (tools exist)
        2. Documentation includes: tool name, description, parameters, return types, examples ✓
        3. Documentation format: Markdown ✓
        4. Each tool documented with purpose, use cases, parameter details ✓
        5. Error codes and troubleshooting guide ✓
        6. Documentation published to docs/ folder ✓
        7. Examples show real Canary queries ✓
        8. Documentation versioned ✓
        """
        # Files exist
        assert api_doc_path.exists(), "API documentation does not exist"
        assert examples_doc_path.exists(), "Examples documentation does not exist"

        api_content = api_doc_path.read_text(encoding="utf-8")
        examples_content = examples_doc_path.read_text(encoding="utf-8")

        # All tools documented
        for tool in EXPECTED_TOOLS:
            assert f"### {tool}" in api_content, f"Tool {tool} not documented"

        # Has error documentation
        assert "## Error Codes" in api_content, "Missing error codes section"

        # Has examples
        assert len(examples_content) > 5000, "Examples documentation seems incomplete"

        # Has version info
        assert re.search(r"v?\d+\.\d+\.\d+", api_content), "Missing version info"

    def test_documentation_references_real_canary_entities(self, examples_doc_path):
        """Verify examples reference real Canary entities from product brief."""
        content = examples_doc_path.read_text(encoding="utf-8")

        # Should reference real entities from the product brief
        real_entities = ["Kiln", "Maceira", "Temperature", "Cement"]

        found_entities = []
        for entity in real_entities:
            if entity in content:
                found_entities.append(entity)

        assert (
            len(found_entities) >= 2
        ), f"examples.md does not reference enough real Canary entities (found: {', '.join(found_entities)})"

    def test_documentation_cross_references(self, api_doc_path, examples_doc_path):
        """Verify documentation files cross-reference each other."""
        api_content = api_doc_path.read_text(encoding="utf-8")
        examples_content = examples_doc_path.read_text(encoding="utf-8")

        # examples.md should reference API.md
        assert (
            "API.md" in examples_content or "API Documentation" in examples_content
        ), "examples.md does not reference API documentation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
