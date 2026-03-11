
from datetime import datetime

usage_data = {
    "requests": 0,
    "tokens": 0
}

def track_usage(tokens: int = 0):
    """Track API usage"""
    usage_data["requests"] += 1
    usage_data["tokens"] += tokens

def get_monthly_usage():
    """Return usage statistics"""
    return {
        "month": datetime.now().strftime("%B"),
        "total_requests": usage_data["requests"],
        "total_tokens": usage_data["tokens"]
    }
