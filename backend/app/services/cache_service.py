import os
import json
import hashlib
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

_redis_client = None
_memory_cache: dict = {}  # In-memory fallback cache


def _get_redis():
    """Get or initialize Redis client (lazy singleton)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        return None

    try:
        import redis

        _redis_client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        logger.info("Redis connection established")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable, falling back to in-memory cache: {e}")
        return None


def compute_cache_key(prefix: str, content: str) -> str:
    """Generate a deterministic cache key from content hash."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"resume_ai:{prefix}:{content_hash}"


def get_cached(key: str) -> Optional[Any]:
    """Retrieve a cached value by key. Returns None if not found or expired."""
    if not CACHE_ENABLED:
        return None

    redis_client = _get_redis()

    if redis_client:
        try:
            raw = redis_client.get(key)
            if raw:
                logger.debug(f"Cache HIT (Redis): {key}")
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")

    # Fall back to in-memory cache
    if key in _memory_cache:
        logger.debug(f"Cache HIT (memory): {key}")
        return _memory_cache[key]

    logger.debug(f"Cache MISS: {key}")
    return None


def set_cached(key: str, value: Any, ttl: int = None) -> bool:
    """Store a value in cache. Returns True on success."""
    if not CACHE_ENABLED:
        return False

    ttl = ttl or CACHE_TTL
    serialized = json.dumps(value, ensure_ascii=False)
    redis_client = _get_redis()

    if redis_client:
        try:
            redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cache SET (Redis): {key}, TTL={ttl}s")
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    # Fall back to in-memory cache (no TTL enforcement for simplicity)
    _memory_cache[key] = value
    logger.debug(f"Cache SET (memory): {key}")
    return True


def delete_cached(key: str) -> bool:
    """Remove a cached entry."""
    redis_client = _get_redis()

    if redis_client:
        try:
            redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")

    _memory_cache.pop(key, None)
    return True


def get_resume_cache_key(resume_id: str) -> str:
    return f"resume_ai:resume:{resume_id}"


def get_match_cache_key(resume_id: str, jd_hash: str) -> str:
    return f"resume_ai:match:{resume_id}:{jd_hash}"


def cache_resume(resume_id: str, resume_data: dict) -> None:
    key = get_resume_cache_key(resume_id)
    set_cached(key, resume_data)


def get_cached_resume(resume_id: str) -> Optional[dict]:
    key = get_resume_cache_key(resume_id)
    return get_cached(key)


def cache_match_result(resume_id: str, job_description: str, match_data: dict) -> None:
    jd_hash = hashlib.md5(job_description.encode()).hexdigest()[:8]
    key = get_match_cache_key(resume_id, jd_hash)
    set_cached(key, match_data)


def get_cached_match(resume_id: str, job_description: str) -> Optional[dict]:
    jd_hash = hashlib.md5(job_description.encode()).hexdigest()[:8]
    key = get_match_cache_key(resume_id, jd_hash)
    return get_cached(key)
