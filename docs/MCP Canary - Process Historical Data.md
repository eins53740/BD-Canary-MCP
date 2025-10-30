# Case : MCP Canary – Process Historical Data

Use this isntructions as well:
https://autopsias.github.io/Hackatonsite/case2.html


# Context
Canary Historian is used to record and provide industrial process data in real-time and high-resolution historical format. This data is essential for performance, quality, and efficiency analysis.
In this case, the goal is to create an MCP (Model Context Protocol) that provides tools to access the organized views in Canary, using the Canary Views Web API. The tools should allow reading of historical, real-time, and metadata related to process variables.

# Case Objective
Develop a proof of concept of a functional MCP that includes specific tools to:
•	Authenticate and connect to the Canary API;
•	Query historical data from a view;
•	Access real-time data (streaming view);
•	Retrieve metadata about tags and their properties.
These tools should enable other applications or AI agents to consume Canary industrial data in a structured and secure way.

# Key Challenges
•	Understand the structure and relevant endpoints of the Canary Views Web API.
•	Implement authentication and token management.
•	Create MCP tools for accessing historical, real-time, and metadata information.
•	Demonstrate data retrieval from a predefined view.

# Available Data / APIs
•	Canary Views Web API: https://readapi.canarylabs.com/25.4/
•	Relevant endpoints: /views, /views/data, /views/metadata.
•	Access to a test endpoint (URI and token provided during the hackathon).
•	Test tags list.

# Success Criteria
•	Build a functional MCP with tools for historical, real-time, and metadata access.
•	Demonstrate real access to data from an existing view.
•	Show an integration example (e.g., comparing historical and real-time data).
•	Explain how the solution could be scaled for real use.

# Useful Resources
•	Canary API Documentation: https://readapi.canarylabs.com/25.4/
•	MCP: https://modelcontextprotocol.io/docs/getting-started/intro
•	REST call examples


# TESTS:

Pytest Commands Quick Reference
Unit only: uv run pytest -m unit -q
Integration only: uv run pytest -m integration -q
Contract only: uv run pytest -m contract -q
All with coverage: uv run pytest --cov=. --cov-report=term-missing -q
Parallel (if needed): uv run pytest -n auto -q



# Linting, Formatting, and Types
Ruff (lint):

Check: uvx ruff check .
Fix: uvx ruff check . --fix
Black (format):

Check: uvx black --check .
Format: uvx black .
Mypy (optional type check):

uv run mypy .




# Local Testing Playbook — Metadata Sync Microservice
This playbook explains how to run the project’s Unit, Integration, and Contract tests on a developer workstation using Python 3.13 and uv for dependency management. It aligns with the Testing Specification (Release 1.0) and the epics/tasks under docs/epics and docs/tasks.

Key goals:
Favor offline tests by default: use fixtures and mocks; gate network tests with an env flag.
Prerequisites
Python 3.13 installed and available on PATH.
uv (dependency and tool runner) installed.
Git (optional for pre-commit hooks).
Install uv:
Windows PowerShell: pipx install uv or py -m pip install --user uv
Create a virtual environment and activate it:

Windows PowerShell
uv venv --python 3.13
./.venv/Scripts/Activate.ps1