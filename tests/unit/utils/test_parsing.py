"""
Tests for the parsing utility functions.
"""

from app.utils.parsing import parse_movie_with_year, is_specific_title_query


class TestParseMovieWithYear:
    """Tests for the parse_movie_with_year function."""

    def test_with_year(self):
        """Test parsing a movie title with a year."""
        title, year = parse_movie_with_year("The Matrix (1999)")
        assert title == "The Matrix"
        assert year == 1999

    def test_without_year(self):
        """Test parsing a movie title without a year."""
        title, year = parse_movie_with_year("Inception")
        assert title == "Inception"
        assert year is None

    def test_with_spaces(self):
        """Test parsing a movie title with spaces."""
        title, year = parse_movie_with_year("The Shawshank Redemption (1994)")
        assert title == "The Shawshank Redemption"
        assert year == 1994

    def test_with_extra_spaces(self):
        """Test parsing a movie title with extra spaces."""
        title, year = parse_movie_with_year("  Pulp Fiction  (1994)  ")
        assert title == "Pulp Fiction"
        assert year == 1994

    def test_with_invalid_year_format(self):
        """Test parsing a movie title with an invalid year format."""
        title, year = parse_movie_with_year("The Godfather (19)")
        assert title == "The Godfather (19)"
        assert year is None

    def test_with_year_not_at_end(self):
        """Test parsing a movie title with a year not at the end."""
        title, year = parse_movie_with_year("(1972) The Godfather")
        assert title == "(1972) The Godfather"
        assert year is None


class TestIsSpecificTitleQuery:
    """Tests for the is_specific_title_query function."""

    def test_semantic_query_with_year(self):
        """Test that semantic queries with a year are identified as NOT specific titles."""
        # "Top horror movies from 1990" contains a year but is a semantic search.
        assert is_specific_title_query("Top horror movies from 1990") is False

    def test_semantic_query_general(self):
        """Test that general semantic queries are identified as NOT specific titles."""
        # "Movies for someone who liked Up" matches discovery patterns.
        assert is_specific_title_query("Movies for someone who liked Up") is False

    def test_specific_title_simple(self):
        """Test that simple specific titles are identified as specific."""
        # "The Matrix" is short enough to be a title.
        assert is_specific_title_query("The Matrix") is True

    def test_specific_title_with_year(self):
        """Test that specific titles with a year are identified as specific."""
        # "The Matrix 1999" has a year and no discovery patterns.
        assert is_specific_title_query("The Matrix 1999") is True

    def test_specific_title_very_short(self):
        """Test that very short specific titles are identified as specific."""
        # "Up" is very short.
        assert is_specific_title_query("Up") is True

    def test_semantic_query_best_of_year(self):
        """Test that 'Best ... of <Year>' is identified as semantic."""
        assert is_specific_title_query("Best movies of 2023") is False

    def test_ambiguous_title_matching_discovery(self):
        """
        Test that titles containing discovery keywords go to AI (semantic).
        This is an acceptable trade-off to support natural language queries.
        """
        # "The Best of Me" contains "Best" -> Discovery -> False (AI)
        assert is_specific_title_query("The Best of Me") is False
