# Story 3.3: Integration with `getTagProperties`

As a **Data Analyst**,
I want the `get_tag_path` tool to use a tag's full metadata in its ranking,
So that the search is more accurate by considering the tag's description and other properties.

**Acceptance Criteria:**
1. The `get_tag_path` tool now calls the `get_tag_metadata` logic for each candidate tag.
2. The scoring algorithm is enhanced to include the tag's `description` and other relevant metadata fields.
3. Keywords found in the description add to the tag's relevance score (with a lower weight than name or path).
4. The tool's response includes the description of the top candidates to provide more context to the user.
5. Validation test: `test_metadata_integration.py` confirms that a tag's description influences its final score.

**Prerequisites:** Story 3.2
