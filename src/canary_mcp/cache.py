"""
Caching layer for Canary MCP Server using SQLite.

Story 2.2: Caching Layer Implementation
Provides local caching with TTL, LRU eviction, and cache bypass support.
"""

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Generator, Optional

from canary_mcp.logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""

    key: str
    value: str  # JSON-encoded value
    created_at: float
    expires_at: float
    access_count: int
    last_accessed: float
    size_bytes: int


class CacheConfig:
    """Configuration for cache behavior."""

    def __init__(self):
        """Initialize cache configuration from environment variables."""
        # Cache location
        self.cache_dir = Path(os.getenv("CANARY_CACHE_DIR", ".cache"))
        self.cache_db = self.cache_dir / "canary_mcp_cache.db"

        # TTL settings (in seconds)
        self.metadata_ttl = int(os.getenv("CANARY_CACHE_METADATA_TTL", "3600"))  # 1 hour
        self.timeseries_ttl = int(os.getenv("CANARY_CACHE_TIMESERIES_TTL", "300"))  # 5 min

        # Size limits
        self.max_cache_size_mb = int(os.getenv("CANARY_CACHE_MAX_SIZE_MB", "100"))
        self.max_cache_size_bytes = self.max_cache_size_mb * 1024 * 1024

        # Eviction settings
        self.eviction_batch_size = 100  # Evict 100 entries when limit reached


class CacheStore:
    """
    SQLite-based cache store with TTL and LRU eviction.

    Provides thread-safe caching with automatic expiration and size-based eviction.
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache store.

        Args:
            config: Cache configuration (uses defaults if not provided)
        """
        self.config = config or CacheConfig()
        self._lock = Lock()
        self._initialized = False

        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def _initialize_db(self) -> None:
        """Initialize SQLite database schema."""
        if self._initialized:
            return

        # Create cache directory if it doesn't exist
        self.config.cache_dir.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL NOT NULL,
                    size_bytes INTEGER NOT NULL
                )
            """)

            # Index for efficient expiration queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON cache_entries(expires_at)
            """)

            # Index for LRU eviction
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed
                ON cache_entries(last_accessed)
            """)

            conn.commit()

        self._initialized = True
        log.info(
            "cache_initialized",
            cache_db=str(self.config.cache_db),
            max_size_mb=self.config.max_cache_size_mb,
        )

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get SQLite connection context manager.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(str(self.config.cache_db))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _generate_cache_key(
        self,
        namespace: str,
        tag: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> str:
        """
        Generate cache key from parameters.

        Args:
            namespace: Namespace identifier
            tag: Tag name or pattern
            start_time: Optional start time for timeseries queries
            end_time: Optional end time for timeseries queries

        Returns:
            str: SHA-256 hash of the parameters
        """
        # Create deterministic key from parameters
        key_parts = [namespace, tag]
        if start_time:
            key_parts.append(start_time)
        if end_time:
            key_parts.append(end_time)

        key_string = ":".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value or None if not found/expired
        """
        self._initialize_db()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT key, value, expires_at, access_count
                    FROM cache_entries
                    WHERE key = ?
                    """,
                    (key,),
                )

                row = cursor.fetchone()
                if not row:
                    self._misses += 1
                    log.debug("cache_miss", key=key[:16])
                    return None

                # Check expiration
                now = time.time()
                if row["expires_at"] < now:
                    # Expired - remove entry
                    conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    conn.commit()
                    self._misses += 1
                    log.debug("cache_expired", key=key[:16])
                    return None

                # Update access stats
                conn.execute(
                    """
                    UPDATE cache_entries
                    SET access_count = access_count + 1,
                        last_accessed = ?
                    WHERE key = ?
                    """,
                    (now, key),
                )
                conn.commit()

                self._hits += 1
                log.debug("cache_hit", key=key[:16], access_count=row["access_count"] + 1)

                # Deserialize value
                try:
                    return json.loads(row["value"])
                except json.JSONDecodeError as e:
                    log.error("cache_deserialize_error", error=str(e), key=key[:16])
                    return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        category: str = "metadata",
    ) -> None:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (uses config default if not provided)
            category: Cache category ("metadata" or "timeseries") for TTL selection
        """
        self._initialize_db()

        # Determine TTL
        if ttl is None:
            ttl = (
                self.config.metadata_ttl
                if category == "metadata"
                else self.config.timeseries_ttl
            )

        # Serialize value
        try:
            value_json = json.dumps(value)
        except (TypeError, ValueError) as e:
            log.error("cache_serialize_error", error=str(e), key=key[:16])
            return

        size_bytes = len(value_json.encode())
        now = time.time()
        expires_at = now + ttl

        with self._lock:
            with self._get_connection() as conn:
                # Check if we need to evict entries
                self._evict_if_needed(conn, size_bytes)

                # Upsert entry
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (key, value, created_at, expires_at, access_count, last_accessed, size_bytes)
                    VALUES (?, ?, ?, ?, 0, ?, ?)
                    """,
                    (key, value_json, now, expires_at, now, size_bytes),
                )
                conn.commit()

        log.debug(
            "cache_set",
            key=key[:16],
            size_bytes=size_bytes,
            ttl=ttl,
            category=category,
        )

    def _evict_if_needed(self, conn: sqlite3.Connection, new_entry_size: int) -> None:
        """
        Evict old entries if cache size limit would be exceeded.

        Args:
            conn: Database connection
            new_entry_size: Size of entry being added
        """
        # Get current cache size
        cursor = conn.execute("SELECT SUM(size_bytes) as total_size FROM cache_entries")
        row = cursor.fetchone()
        current_size = row["total_size"] or 0

        # Check if we need to evict
        if current_size + new_entry_size <= self.config.max_cache_size_bytes:
            return

        # Evict LRU entries until we have space
        target_size = self.config.max_cache_size_bytes - new_entry_size
        evicted = 0

        while current_size > target_size:
            # Delete batch of least recently accessed entries
            cursor = conn.execute(
                """
                SELECT key, size_bytes
                FROM cache_entries
                ORDER BY last_accessed ASC
                LIMIT ?
                """,
                (self.config.eviction_batch_size,),
            )

            entries = cursor.fetchall()
            if not entries:
                break

            for entry in entries:
                conn.execute("DELETE FROM cache_entries WHERE key = ?", (entry["key"],))
                current_size -= entry["size_bytes"]
                evicted += 1

        if evicted > 0:
            conn.commit()
            self._evictions += evicted
            log.info(
                "cache_eviction",
                evicted_count=evicted,
                new_size_mb=current_size / (1024 * 1024),
            )

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: SQL LIKE pattern for keys (None = invalidate all)

        Returns:
            int: Number of entries invalidated
        """
        self._initialize_db()

        with self._lock:
            with self._get_connection() as conn:
                if pattern:
                    cursor = conn.execute(
                        "DELETE FROM cache_entries WHERE key LIKE ?",
                        (pattern,),
                    )
                else:
                    cursor = conn.execute("DELETE FROM cache_entries")

                conn.commit()
                count = cursor.rowcount

        log.info("cache_invalidated", pattern=pattern, count=count)
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            int: Number of entries removed
        """
        self._initialize_db()

        now = time.time()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM cache_entries WHERE expires_at < ?",
                    (now,),
                )
                conn.commit()
                count = cursor.rowcount

        if count > 0:
            log.info("cache_cleanup", expired_count=count)

        return count

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Statistics including hits, misses, size, entry count
        """
        self._initialize_db()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as entry_count,
                    SUM(size_bytes) as total_size,
                    SUM(access_count) as total_accesses
                FROM cache_entries
                """
            )
            row = cursor.fetchone()

            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "entry_count": row["entry_count"] or 0,
                "total_size_bytes": row["total_size"] or 0,
                "total_size_mb": (row["total_size"] or 0) / (1024 * 1024),
                "max_size_mb": self.config.max_cache_size_mb,
                "cache_hits": self._hits,
                "cache_misses": self._misses,
                "hit_rate_percent": hit_rate,
                "evictions": self._evictions,
                "total_accesses": row["total_accesses"] or 0,
            }


# Global cache store instance
_cache_store: Optional[CacheStore] = None


def get_cache_store() -> CacheStore:
    """
    Get the global cache store instance.

    Returns:
        CacheStore: The global cache store
    """
    global _cache_store
    if _cache_store is None:
        _cache_store = CacheStore()
    return _cache_store
