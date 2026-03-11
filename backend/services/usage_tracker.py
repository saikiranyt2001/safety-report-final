from datetime import datetime

usage_data = {
    "requests": 0,
    "tokens": 0
}

def track_usage(tokens: int = 0):
    """Track API usage"""
    usage_data["requests"] += 1
    usage_data["tokens"] += tokens


def get_monthly_usage(month: str | None = None):
    """Return usage statistics"""

    return {
        "month": month or datetime.now().strftime("%Y-%m"),
        "total_requests": usage_data["requests"],
        "total_tokens": usage_data["tokens"]
    }