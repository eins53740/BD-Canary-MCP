"""Utility functions for hash-based embeddings used by the local vector index."""

from __future__ import annotations

import hashlib
import re
from typing import List

import numpy as np

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> List[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text or "")]


def hash_embedding(
    text: str,
    *,
    dimension: int = 512,
    seed: int = 0,
) -> np.ndarray:
    """Produce a deterministic embedding by hashing tokens into a fixed bucket."""
    if dimension <= 0:
        raise ValueError("dimension must be positive")

    vector = np.zeros(dimension, dtype=np.float32)
    tokens = tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(f"{seed}-{token}".encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dimension
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[idx] += sign

    norm = np.linalg.norm(vector)
    if norm:
        vector /= norm
    return vector
