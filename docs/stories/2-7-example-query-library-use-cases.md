# Story 2.7: Example Query Library & Use Cases

As a **Plant Engineer**,
I want a library of example queries for common plant data analysis scenarios,
So that I can quickly learn how to use the MCP server for my daily tasks.

**Acceptance Criteria:**
1. Example query library created with 15-20 common use cases
2. Examples cover: temperature trends, cross-tag comparisons, anomaly detection, quality issues
3. Each example includes: natural language query, expected MCP tool calls, sample response
4. Examples organized by use case category: validation, troubleshooting, optimization, reporting
5. Examples include queries for all 5 MCP tools
6. Interactive examples: users can copy/paste into Claude Desktop
7. Examples reference real-world scenarios from Product Brief (Kiln 6, Maceira plant, etc.)
8. Example library published in docs/ and README
9. Include integration example comparing historical vs recent data (e.g., "Compare Kiln 6 temperature: last week average vs last minute value")
10. Validation test: `test_examples.py` confirms all example queries are valid and return expected results

**Prerequisites:** Story 2.6 (API documentation)
