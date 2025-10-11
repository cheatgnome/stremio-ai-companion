"""
Service classes for the Stremio AI Companion application.
"""

from .llm import LLMService
from .tmdb import TMDBService
from .rpdb import RPDBService
from .encryption import encryption_service

import datetime


def get_next_tuesday():
    """Get the next Tuesday at midnight UTC."""
    today = datetime.datetime.now(datetime.timezone.utc)
    days_ahead = 1 - today.weekday()  # Tuesday is 1 (Monday is 0)
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    next_tuesday = today + datetime.timedelta(days=days_ahead)
    return next_tuesday.replace(hour=0, minute=0, second=0, microsecond=0)


def get_tuesday_to_tuesday_ttl():
    """Get TTL in seconds from now until next Tuesday."""
    next_tuesday = get_next_tuesday()
    now = datetime.datetime.now(datetime.timezone.utc)
    return int((next_tuesday - now).total_seconds())


CATALOG_PROMPTS = {
    "trending": {
        "title": "Trending this week",
        "prompt": "Show me what's trending this week on streaming services and (P)VOD (or Blu-ray releases if relevant).",
        "cache_ttl": get_tuesday_to_tuesday_ttl,  # Dynamic TTL until next Tuesday
    },
    "new_releases": {
        "title": "Recent Releases",
        "prompt": "Show me highly-rated new releases from the past 6 months that have received positive reception.",
        "cache_ttl": 172800,  # 48 hours
    },
    "critics_picks": {
        "title": "Critics' Picks",
        "prompt": "Show me highly-rated titles from critics, award winners, and critically acclaimed works from any era.",
        "cache_ttl": 604800,  # 7 days
    },
    "hidden_gems": {
        "title": "Hidden Gems",
        "prompt": "Show me underrated, lesser-known, or overlooked titles worth watching that deserve more recognition.",
        "cache_ttl": 1209600,  # 14 days
    },
}
