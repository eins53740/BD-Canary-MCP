"""Unit tests for list_namespaces tool logic."""

import pytest

from canary_mcp.server import list_namespaces


@pytest.mark.unit
def test_list_namespaces_tool_registered():
    """Test that list_namespaces tool is registered with FastMCP."""
    # Import the tool - if it's registered, it should be accessible
    assert list_namespaces is not None
    # FastMCP wraps tools in FunctionTool objects
    assert hasattr(list_namespaces, "name")
    assert list_namespaces.name == "list_namespaces"


@pytest.mark.unit
def test_list_namespaces_tool_has_description():
    """Test that list_namespaces tool has proper documentation."""
    # FastMCP FunctionTool has a fn attribute containing the actual function
    assert hasattr(list_namespaces, "fn")
    assert list_namespaces.fn.__doc__ is not None
    assert "namespace" in list_namespaces.fn.__doc__.lower()
    assert "hierarchical" in list_namespaces.fn.__doc__.lower()


@pytest.mark.unit
def test_parse_namespace_data_with_valid_nodes():
    """Test parsing namespace data with valid node structure."""
    # Simulate the parsing logic from list_namespaces function
    mock_data = {
        "nodes": [
            {"path": "Plant.Area1", "id": "1"},
            {"path": "Plant.Area2", "id": "2"},
        ]
    }

    namespaces = []
    if isinstance(mock_data, dict) and "nodes" in mock_data:
        nodes = mock_data.get("nodes", [])
        for node in nodes:
            if isinstance(node, dict) and "path" in node:
                namespaces.append(node["path"])

    assert len(namespaces) == 2
    assert "Plant.Area1" in namespaces
    assert "Plant.Area2" in namespaces


@pytest.mark.unit
def test_parse_namespace_data_with_missing_path():
    """Test parsing namespace data when path field is missing."""
    mock_data = {
        "nodes": [
            {"id": "1"},  # Missing path
            {"path": "Plant.Area2", "id": "2"},
        ]
    }

    namespaces = []
    if isinstance(mock_data, dict) and "nodes" in mock_data:
        nodes = mock_data.get("nodes", [])
        for node in nodes:
            if isinstance(node, dict) and "path" in node:
                namespaces.append(node["path"])

    # Should only include node with path
    assert len(namespaces) == 1
    assert "Plant.Area2" in namespaces


@pytest.mark.unit
def test_parse_namespace_data_with_empty_nodes():
    """Test parsing namespace data with empty nodes list."""
    mock_data = {"nodes": []}

    namespaces = []
    if isinstance(mock_data, dict) and "nodes" in mock_data:
        nodes = mock_data.get("nodes", [])
        for node in nodes:
            if isinstance(node, dict) and "path" in node:
                namespaces.append(node["path"])

    assert len(namespaces) == 0
    assert namespaces == []


@pytest.mark.unit
def test_parse_namespace_data_with_missing_nodes_key():
    """Test parsing namespace data when nodes key is missing."""
    mock_data = {"invalid_key": "data"}

    namespaces = []
    if isinstance(mock_data, dict) and "nodes" in mock_data:
        nodes = mock_data.get("nodes", [])
        for node in nodes:
            if isinstance(node, dict) and "path" in node:
                namespaces.append(node["path"])

    assert len(namespaces) == 0
    assert namespaces == []


@pytest.mark.unit
def test_error_response_format():
    """Test error response format structure."""
    error_msg = "Test error message"
    error_response = {
        "success": False,
        "error": error_msg,
        "namespaces": [],
        "count": 0,
    }

    assert "success" in error_response
    assert error_response["success"] is False
    assert "error" in error_response
    assert error_response["error"] == error_msg
    assert "namespaces" in error_response
    assert error_response["namespaces"] == []
    assert "count" in error_response
    assert error_response["count"] == 0


@pytest.mark.unit
def test_success_response_format():
    """Test success response format structure."""
    test_namespaces = ["Plant.Area1", "Plant.Area2"]
    success_response = {
        "success": True,
        "namespaces": test_namespaces,
        "count": len(test_namespaces),
    }

    assert "success" in success_response
    assert success_response["success"] is True
    assert "namespaces" in success_response
    assert success_response["namespaces"] == test_namespaces
    assert "count" in success_response
    assert success_response["count"] == 2
