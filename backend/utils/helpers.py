# backend/utils/helpers.py

import redis
import json
from backend.core.config import settings

# Redis connection
r = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

def split_text(text: str, chunk_size: int = 500):
    """
    Split long text into chunks for RAG processing
    """
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]

def get_cached_report(key: str):
    """
    Retrieve cached report from Redis
    """
    data = r.get(key)
    if data:
        return json.loads(data)
    return None

def cache_report(key: str, value, ttl: int = 300):
    """
    Store report in Redis cache
    """
    r.set(
        key,
        json.dumps(value),
        ex=ttl
    )
# Helper functions for AI Safety Platform

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

def split_text(text, chunk_size=500):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def get_cached_report(key):
    return r.get(key)

def cache_report(key, value):
    r.set(key, value, ex=300)
