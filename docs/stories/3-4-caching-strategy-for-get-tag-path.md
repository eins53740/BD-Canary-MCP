# Story 3.4: Caching Strategy for `get_tag_path`

As a **Developer**,
I want the `get_tag_path` tool to cache its results,
So that repeated queries are faster and the load on the Canary API is reduced.

**Acceptance Criteria:**
1. The `get_tag_path` tool is integrated with the existing caching store (`get_cache_store()`)
2. Intermediate API calls (`browseTags`, `getTagProperties`) made within the tool are cached.
3. The final ranked result of a `get_tag_path` query is itself cached.
4. The cache can be bypassed with a `bypass_cache` parameter in the tool.
5. Cache hit/miss rates for this tool are added to the server's metrics.
6. Validation test: `test_get_tag_path_caching.py` confirms that repeated calls are served from the cache and that the bypass works.

**Prerequisites:** Story 3.3, Story 2.2 (Caching Layer Implementation)
