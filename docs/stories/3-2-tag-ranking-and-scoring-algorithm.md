# Story 3.2: Tag Ranking and Scoring Algorithm

As a **Data Analyst**,
I want the `get_tag_path` tool to intelligently rank search results,
So that the most relevant tag is presented first.

**Acceptance Criteria:**
1. A scoring algorithm is implemented within the `get_tag_path` tool.
2. The algorithm calculates a relevance score for each candidate tag.
3. Scoring is weighted, prioritizing keywords found in the tag's `name` over its `path`.
4. The candidate list returned by the tool is sorted by this score in descending order.
5. The top-scoring tag is identified as the `most_likely_path` in the response.
6. Validation test: `test_tag_scoring.py` confirms that known tags are scored and ranked correctly based on test queries.

**Prerequisites:** Story 3.1
