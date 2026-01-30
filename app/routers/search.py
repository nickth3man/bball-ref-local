"""Search API router for global search across players, teams, and games.

Provides a unified search endpoint that returns results grouped by type.
Supports both JSON API responses and HTMX partial HTML responses.
"""

import html
import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.services.database import execute_query
from app.services.htmx_utils import get_templates, is_htmx_request


def _sanitize_query(query: str) -> str:
    """Sanitize user search query to prevent XSS attacks.
    
    Strips HTML tags and escapes special characters.
    
    Args:
        query: Raw user input query string.
        
    Returns:
        Sanitized query string safe for HTML rendering.
    """
    # Remove HTML tags
    query = re.sub(r'<[^>]+>', '', query)
    # Escape special HTML characters
    query = html.escape(query)
    return query

router = APIRouter(prefix="/api/v1", tags=["search"])


class SearchResult(BaseModel):
    """Single search result item.

    Attributes:
        type: Result type ("player", "team", "game").
        id: Unique identifier for the item.
        name: Display name of the result.
        subtitle: Secondary information (team for players, score for games).
        url: URL path to the detail page.
    """

    model_config = ConfigDict(from_attributes=True)

    type: str = Field(description="Result type (player, team, game)")
    id: str | int = Field(description="Unique identifier for the item")
    name: str = Field(description="Display name of the result")
    subtitle: str = Field(description="Secondary information")
    url: str = Field(description="Link to detail page")


class SearchResponse(BaseModel):
    """Search response with grouped results.

    Attributes:
        query: The original search query.
        results: List of search results ordered by relevance.
        total: Total number of results found.
    """

    model_config = ConfigDict(from_attributes=True)

    query: str = Field(description="The original search query")
    results: list[SearchResult] = Field(description="List of search results")
    total: int = Field(description="Total number of results", ge=0)


def _search_players(query: str, limit: int) -> list[SearchResult]:
    """Search players by first name, last name, or full name.

    Args:
        query: Search query string.
        limit: Maximum results to return.

    Returns:
        List of player search results ordered by relevance.
    """
    search_pattern = f"%{query}%"
    exact_pattern = query.lower()

    # Search with relevance ordering - exact matches first
    sql = """
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.position,
            t.full_name as team_name,
            t.abbreviation as team_abbr,
            CASE
                WHEN LOWER(p.first_name) = ? OR LOWER(p.last_name) = ?
                     OR LOWER(p.first_name || ' ' || p.last_name) = ?
                THEN 0
                ELSE 1
            END as relevance
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.first_name ILIKE ?
           OR p.last_name ILIKE ?
           OR (p.first_name || ' ' || p.last_name) ILIKE ?
        ORDER BY relevance, p.last_name, p.first_name
        LIMIT ?
    """

    rows = execute_query(
        sql,
        [
            exact_pattern,
            exact_pattern,
            exact_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ],
    )

    results = []
    for row in rows:
        player_id, first_name, last_name, position, team_name, team_abbr, _ = row
        full_name = f"{first_name} {last_name}"
        subtitle = f"{team_abbr} - {position}" if team_abbr else position

        results.append(
            SearchResult(
                type="player",
                id=player_id,
                name=full_name,
                subtitle=subtitle,
                url=f"/players/{player_id}",
            )
        )

    return results


def _search_teams(query: str, limit: int) -> list[SearchResult]:
    """Search teams by name, abbreviation, nickname, or city.

    Args:
        query: Search query string.
        limit: Maximum results to return.

    Returns:
        List of team search results ordered by relevance.
    """
    search_pattern = f"%{query}%"
    exact_pattern = query.lower()

    sql = """
        SELECT
            team_id,
            full_name,
            abbreviation,
            nickname,
            city,
            conference,
            division,
            CASE
                WHEN LOWER(abbreviation) = ? OR LOWER(nickname) = ?
                     OR LOWER(city) = ? OR LOWER(full_name) = ?
                THEN 0
                ELSE 1
            END as relevance
        FROM teams
        WHERE full_name ILIKE ?
           OR abbreviation ILIKE ?
           OR nickname ILIKE ?
           OR city ILIKE ?
        ORDER BY relevance, full_name
        LIMIT ?
    """

    rows = execute_query(
        sql,
        [
            exact_pattern,
            exact_pattern,
            exact_pattern,
            exact_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            search_pattern,
            limit,
        ],
    )

    results = []
    for row in rows:
        # Unpack row - handle both 7 columns (without relevance) and 8 columns (with relevance)
        if len(row) == 8:
            team_id, full_name, abbreviation, _nickname, _city, conference, division, _ = row
        else:
            team_id, full_name, abbreviation, _nickname, _city, conference, division = row
        subtitle = f"{conference} - {division}"

        results.append(
            SearchResult(
                type="team", id=str(team_id), name=full_name, subtitle=subtitle, url=f"/teams/{team_id}"
            )
        )

    return results


def _search_games(query: str, limit: int) -> list[SearchResult]:
    """Search games by team names involved.

    Args:
        query: Search query string.
        limit: Maximum results to return.

    Returns:
        List of game search results ordered by date (most recent first).
    """
    search_pattern = f"%{query}%"

    sql = """
        SELECT
            g.game_id,
            g.game_date,
            g.home_score,
            g.away_score,
            ht.full_name as home_team_name,
            at.full_name as away_team_name,
            ht.abbreviation as home_team_abbr,
            at.abbreviation as away_team_abbr,
            g.season
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        WHERE ht.full_name ILIKE ?
           OR ht.nickname ILIKE ?
           OR ht.abbreviation ILIKE ?
           OR at.full_name ILIKE ?
           OR at.nickname ILIKE ?
           OR at.abbreviation ILIKE ?
        ORDER BY g.game_date DESC
        LIMIT ?
    """

    rows = execute_query(sql, [search_pattern] * 6 + [limit])

    results = []
    for row in rows:
        (
            game_id,
            game_date,
            home_score,
            away_score,
            home_team,
            away_team,
            home_abbr,
            away_abbr,
            season,
        ) = row

        name = f"{home_abbr} vs {away_abbr}"
        score_display = (
            f"{home_score}-{away_score}"
            if home_score is not None and away_score is not None
            else "Scheduled"
        )
        subtitle = f"{game_date.strftime('%b %d, %Y')} - {score_display}"

        results.append(
            SearchResult(
                type="game", id=game_id, name=name, subtitle=subtitle, url=f"/games/{game_id}"
            )
        )

    return results


@router.get("/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: Annotated[str, Query(description="Search query string", min_length=1, max_length=100)],
    limit: Annotated[int, Query(description="Maximum results per type", ge=1, le=20)] = 10,
) -> SearchResponse | HTMLResponse:
    """Global search across players, teams, and games.

    Query Parameters:
        - q: Search query string (required, 1-100 characters)
        - limit: Maximum results per type (default: 10, max: 20)

    Returns:
        Search results grouped by type. Returns HTML partial if HTMX request.

    Search Logic:
        - Players: Searches first_name, last_name, full_name
        - Teams: Searches full_name, abbreviation, nickname, city
        - Games: Searches team names involved

        Results are ordered by relevance (exact matches first) and limited
        per type (players: 5, teams: 3, games: 2) based on the limit parameter.

    Raises:
        HTTPException: 500 if database query fails.
    """
    # Calculate limits per type (distribute evenly)
    player_limit = max(1, min(limit // 2, 8))
    team_limit = max(1, min(limit // 3, 5))
    game_limit = max(1, limit - player_limit - team_limit)

    # Sanitize query for safe HTML rendering (prevents XSS)
    sanitized_query = _sanitize_query(q)

    try:
        # Search all types in parallel (well, sequentially but grouped)
        player_results = _search_players(q, player_limit)
        team_results = _search_teams(q, team_limit)
        game_results = _search_games(q, game_limit)

        # Combine results: players first, then teams, then games
        all_results = player_results + team_results + game_results

        response_data = SearchResponse(query=sanitized_query, results=all_results, total=len(all_results))

        # Return HTML if HTMX request
        if is_htmx_request(request):
            templates = get_templates()
            return templates.TemplateResponse(
                "partials/search_results.html",
                {
                    "request": request,
                    "query": sanitized_query,
                    "results": all_results,
                    "total": len(all_results),
                    "players": player_results,
                    "teams": team_results,
                    "games": game_results,
                },
            )

        return response_data

    except Exception as e:
        # Log the actual error for debugging but don't expose internals to client
        import logging
        logging.getLogger(__name__).error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred during search.") from e
