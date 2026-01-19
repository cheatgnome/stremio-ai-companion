"""
TMDB service for the Stremio AI Companion application.
"""

import difflib
import logging
from typing import Any, Optional, List

import httpx
from pydantic import BaseModel, ConfigDict


class TMDBSearchParams(BaseModel):
    """Parameters for TMDB search requests."""

    model_config = ConfigDict(frozen=True)

    query: str
    language: str
    page: int = 1
    year: Optional[int] = None


class TMDBMovieSearchParams(TMDBSearchParams):
    """Parameters specific to movie search requests."""

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        params = {
            "query": self.query,
            "include_adult": "false",
            "language": self.language,
            "page": str(self.page),
        }
        if self.year:
            params["primary_release_year"] = str(self.year)
        return params


class TMDBTVSearchParams(TMDBSearchParams):
    """Parameters specific to TV search requests."""

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        params = {
            "query": self.query,
            "include_adult": "false",
            "language": self.language,
            "page": str(self.page),
        }
        if self.year:
            params["first_air_date_year"] = str(self.year)
        return params


class TMDBDetailsParams(BaseModel):
    """Parameters for TMDB details requests."""

    model_config = ConfigDict(frozen=True)

    language: str
    append_to_response: str = "external_ids"

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        return {
            "language": self.language,
            "append_to_response": self.append_to_response,
        }


class TMDBService:
    """
    Service for interacting with The Movie Database (TMDB) API.

    This service handles searching for movies and retrieving movie details
    from the TMDB API.
    """

    def __init__(
        self,
        read_access_token: str,
        language: str,
        timeout: float = 10.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        """
        Initialize the TMDB service with an access token.

        Args:
            read_access_token: TMDB API read access token
            language: Language code for API requests
            timeout: HTTP request timeout in seconds
            client: Optional shared httpx.AsyncClient
        """
        self.read_access_token = read_access_token
        self.base_url = "https://api.themoviedb.org/3"
        self.timeout = timeout
        self.logger = logging.getLogger("stremio_ai_companion.TMDBService")
        self.language = language
        self.client = client

    @property
    def _headers(self) -> dict[str, str]:
        """
        Get the headers required for TMDB API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {"accept": "application/json", "Authorization": f"Bearer {self.read_access_token}"}

    async def _make_request(self, endpoint: str, params: dict[str, str]) -> Optional[dict[str, Any]]:
        """
        Make an HTTP request to the TMDB API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters

        Returns:
            Response data or None if request failed
        """
        if self.client:
            return await self._execute_request(self.client, endpoint, params)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await self._execute_request(client, endpoint, params)

    async def _execute_request(
        self, client: httpx.AsyncClient, endpoint: str, params: dict[str, str]
    ) -> Optional[dict[str, Any]]:
        """Execute the request with the given client."""
        try:
            response = await client.get(f"{self.base_url}/{endpoint}", params=params, headers=self._headers)
            response.raise_for_status()

            if response.status_code == 401:
                self.logger.error("TMDB API authentication failed - check read access token")
                return None

            return response.json()

        except httpx.TimeoutException:
            self.logger.warning(f"TMDB request timeout for endpoint: {endpoint}")
            return None
        except httpx.HTTPStatusError as e:
            self.logger.error(f"TMDB HTTP error {e.response.status_code} for endpoint: {endpoint}")
            return None
        except Exception as e:
            self.logger.error(f"TMDB request error for {endpoint}: {e}")
            return None

    async def search_movie(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> List[dict[str, Any]]:
        """
        Search for a movie by title and optional year.

        Args:
            title: Movie title to search for
            year: Optional release year to filter by

        Returns:
            List of dictionaries with movie data or empty list if not found
        """
        self.logger.debug(f"Searching TMDB for movie: '{title}'" + (f" ({year})" if year else ""))

        search_params = TMDBMovieSearchParams(query=title, year=year, language=self.language)

        data = await self._make_request("search/movie", search_params.api_params)

        if not data or not data.get("results"):
            self.logger.warning(f"No TMDB results found for movie '{title}'" + (f" ({year})" if year else ""))
            return []

        # Thresholds
        FUZZY_MATCH_THRESHOLD = 0.85
        RELAXED_MATCH_THRESHOLD = 0.65
        TOP_RESULT_THRESHOLD = 0.40

        matches = []
        tmdb_results = data["results"]

        for index, res in enumerate(tmdb_results):
            res_title = res.get("title", "")

            # Exact match
            if res_title.lower() == title.lower():
                res["_score"] = 1.0
                matches.append(res)
                continue

            score = difflib.SequenceMatcher(None, title.lower(), res_title.lower()).ratio()
            res["_score"] = score

            # Keep if high enough score
            if score >= FUZZY_MATCH_THRESHOLD:
                matches.append(res)
            # Keep if relaxed score
            elif score >= RELAXED_MATCH_THRESHOLD:
                matches.append(res)
            # Keep top result if it has a decent score
            elif index == 0 and score >= TOP_RESULT_THRESHOLD:
                matches.append(res)

        # Deduplicate by ID
        unique_matches = []
        seen_ids = set()
        for m in matches:
            if m["id"] not in seen_ids:
                unique_matches.append(m)
                seen_ids.add(m["id"])

        # Sort by score descending
        unique_matches.sort(key=lambda x: x.get("_score", 0), reverse=True)

        if unique_matches:
            top_matches = unique_matches[:5]
            self.logger.debug(
                f"Found {len(top_matches)} TMDB results for '{title}': {[m.get('title') for m in top_matches]}"
            )
            return top_matches

        self.logger.info(f"No close match found for movie '{title}'. Triggering AI fallback.")
        return []

    async def search_tv(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> List[dict[str, Any]]:
        """
        Search for a TV series by title and optional year.

        Args:
            title: TV series title to search for
            year: Optional first air date year to filter by

        Returns:
            List of dictionaries with TV series data or empty list if not found
        """
        self.logger.debug(f"Searching TMDB for TV series: '{title}'" + (f" ({year})" if year else ""))

        search_params = TMDBTVSearchParams(query=title, year=year, language=self.language)

        data = await self._make_request("search/tv", search_params.api_params)

        if not data or not data.get("results"):
            self.logger.warning(f"No TMDB results found for series '{title}'" + (f" ({year})" if year else ""))
            return []

        # Thresholds
        FUZZY_MATCH_THRESHOLD = 0.85
        RELAXED_MATCH_THRESHOLD = 0.65
        TOP_RESULT_THRESHOLD = 0.40

        matches = []
        tmdb_results = data["results"]

        for index, res in enumerate(tmdb_results):
            res_name = res.get("name", "")

            # Exact match
            if res_name.lower() == title.lower():
                res["_score"] = 1.0
                matches.append(res)
                continue

            score = difflib.SequenceMatcher(None, title.lower(), res_name.lower()).ratio()
            res["_score"] = score

            # Keep if high enough score
            if score >= FUZZY_MATCH_THRESHOLD:
                matches.append(res)
            # Keep if relaxed score
            elif score >= RELAXED_MATCH_THRESHOLD:
                matches.append(res)
            # Keep top result if it has a decent score
            elif index == 0 and score >= TOP_RESULT_THRESHOLD:
                matches.append(res)

        # Deduplicate by ID
        unique_matches = []
        seen_ids = set()
        for m in matches:
            if m["id"] not in seen_ids:
                unique_matches.append(m)
                seen_ids.add(m["id"])

        # Sort by score descending
        unique_matches.sort(key=lambda x: x.get("_score", 0), reverse=True)

        if unique_matches:
            top_matches = unique_matches[:5]
            self.logger.debug(
                f"Found {len(top_matches)} TMDB results for '{title}': {[m.get('name') for m in top_matches]}"
            )
            return top_matches

        self.logger.info(f"No close match found for series '{title}'. Triggering AI fallback.")
        return []

    async def get_movie_details(self, movie_id: int) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a movie by ID.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Dictionary with movie details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for movie ID: {movie_id}")

        details_params = TMDBDetailsParams(language=self.language)
        data = await self._make_request(f"movie/{movie_id}", details_params.api_params)

        if data:
            self.logger.debug(f"Successfully fetched details for movie ID {movie_id}: {data.get('title', 'Unknown')}")

        return data

    async def get_tv_details(self, tv_id: int) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a TV series by ID.

        Args:
            tv_id: TMDB TV series ID

        Returns:
            Dictionary with TV series details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for TV series ID: {tv_id}")

        details_params = TMDBDetailsParams(language=self.language)
        data = await self._make_request(f"tv/{tv_id}", details_params.api_params)

        if data:
            self.logger.debug(f"Successfully fetched details for TV series ID {tv_id}: {data.get('name', 'Unknown')}")

        return data
