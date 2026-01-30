"""Teams API router for basketball statistics.

Provides REST API endpoints for team information, rosters, stats, and games.
Supports both JSON API responses and HTMX partial template rendering.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.models import Player, Team
from app.models.game import Game
from app.models.responses import GameListResponse
from app.services.database import execute_query
from app.services.htmx_utils import is_htmx_request

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@router.get("/", response_model=None)
async def list_teams(
    request: Request,
    conference: Annotated[
        str | None, Query(description="Filter by conference (Eastern or Western)")
    ] = None,
    division: Annotated[
        str | None,
        Query(
            description="Filter by division (Atlantic, Central, Southeast, Northwest, Pacific, Southwest)"
        ),
    ] = None,
) -> list[Team] | HTMLResponse:
    """List all teams with optional filtering.

    Query Parameters:
        conference: Filter teams by conference (Eastern or Western).
        division: Filter teams by division.

    Returns:
        A list of Team models, or an HTML partial if HTMX request.

    Raises:
        HTTPException: 500 if database query fails.
    """
    try:
        query = """
            SELECT
                team_id,
                full_name,
                abbreviation,
                nickname,
                city,
                state,
                year_founded,
                arena,
                owner,
                general_manager,
                head_coach,
                conference,
                division
            FROM teams
            WHERE 1=1
        """
        params: list = []

        if conference:
            query += " AND conference = ?"
            params.append(conference)

        if division:
            query += " AND division = ?"
            params.append(division)

        query += " ORDER BY conference, division, city"

        results = execute_query(query, params)
        teams = [
            Team(
                **dict(
                    zip(
                        [
                            "team_id",
                            "full_name",
                            "abbreviation",
                            "nickname",
                            "city",
                            "state",
                            "year_founded",
                            "arena",
                            "owner",
                            "general_manager",
                            "head_coach",
                            "conference",
                            "division",
                        ],
                        row,
                        strict=True,
                    )
                )
            )
            for row in results
        ]

        if is_htmx_request(request):
            return HTMLResponse(content="")  # Placeholder for team_list.html

        return teams
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch teams: {e}") from e


@router.get("/{team_id}", response_model=None)
async def get_team(
    request: Request,
    team_id: int,
) -> Team | HTMLResponse:
    """Get detailed information for a specific team.

    Path Parameters:
        team_id: The unique identifier for the team.

    Returns:
        Team model with additional information, or an HTML partial if HTMX request.

    Raises:
        HTTPException: 404 if team not found, 500 if database query fails.
    """
    try:
        query = """
            SELECT
                team_id,
                full_name,
                abbreviation,
                nickname,
                city,
                state,
                year_founded,
                arena,
                owner,
                general_manager,
                head_coach,
                conference,
                division
            FROM teams
            WHERE team_id = ?
        """
        result = execute_query(query, [team_id])

        if not result:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

        team = Team(
            **dict(
                zip(
                    [
                        "team_id",
                        "full_name",
                        "abbreviation",
                        "nickname",
                        "city",
                        "state",
                        "year_founded",
                        "arena",
                        "owner",
                        "general_manager",
                        "head_coach",
                        "conference",
                        "division",
                    ],
                    result[0],
                    strict=True,
                )
            )
        )

        if is_htmx_request(request):
            return HTMLResponse(content="")  # Placeholder for team_card.html

        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team: {e}") from e


@router.get("/{team_id}/roster", response_model=None)
async def get_team_roster(
    request: Request,
    team_id: int,
) -> list[Player] | HTMLResponse:
    """Get the current roster for a specific team.

    Path Parameters:
        team_id: The unique identifier for the team.

    Returns:
        List of Player models on the team's current roster, or an HTML partial if HTMX request.

    Raises:
        HTTPException: 404 if team not found, 500 if database query fails.
    """
    try:
        # First verify team exists
        team_check = execute_query("SELECT 1 FROM teams WHERE team_id = ?", [team_id])
        if not team_check:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

        query = """
            SELECT
                player_id,
                first_name,
                last_name,
                team_id,
                position,
                jersey_number,
                height,
                weight,
                birth_date,
                country,
                draft_year,
                draft_round,
                draft_number
            FROM players
            WHERE team_id = ?
            ORDER BY last_name, first_name
        """
        results = execute_query(query, [team_id])

        players = [
            Player(
                **dict(
                    zip(
                        [
                            "player_id",
                            "first_name",
                            "last_name",
                            "team_id",
                            "position",
                            "jersey_number",
                            "height",
                            "weight",
                            "birth_date",
                            "country",
                            "draft_year",
                            "draft_round",
                            "draft_number",
                        ],
                        row,
                        strict=True,
                    )
                )
            )
            for row in results
        ]

        if is_htmx_request(request):
            return HTMLResponse(content="")  # Placeholder for roster_table.html

        return players
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch roster: {e}") from e


@router.get("/{team_id}/stats", response_model=None)
async def get_team_stats(
    request: Request,
    team_id: int,
    season: Annotated[
        int, Query(description="Season year (e.g., 2024 for 2023-24 season)", ge=1946)
    ],
) -> dict | HTMLResponse:
    """Get season statistics for a specific team.

    Path Parameters:
        team_id: The unique identifier for the team.

    Query Parameters:
        season: The season year to get statistics for (required).

    Returns:
        Team season statistics, or an HTML partial if HTMX request.

    Raises:
        HTTPException: 404 if team not found, 500 if database query fails.
    """
    try:
        # First verify team exists
        team_check = execute_query("SELECT 1 FROM teams WHERE team_id = ?", [team_id])
        if not team_check:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

        # Aggregate team stats from player_game_stats and games
        query = """
            SELECT
                COUNT(DISTINCT g.game_id) as games_played,
                SUM(CASE WHEN g.winner_team_id = ? THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN g.winner_team_id != ? AND g.winner_team_id IS NOT NULL THEN 1 ELSE 0 END) as losses,
                AVG(pgs.points) as avg_points_for,
                SUM(pgs.points) as total_points_for,
                SUM(pgs.fg_made) as total_fg_made,
                SUM(pgs.fg_attempted) as total_fg_attempted,
                SUM(pgs.fg3_made) as total_fg3_made,
                SUM(pgs.fg3_attempted) as total_fg3_attempted,
                SUM(pgs.ft_made) as total_ft_made,
                SUM(pgs.ft_attempted) as total_ft_attempted,
                SUM(pgs.rebounds_offensive) as total_offensive_rebounds,
                SUM(pgs.rebounds_defensive) as total_defensive_rebounds,
                SUM(pgs.assists) as total_assists,
                SUM(pgs.steals) as total_steals,
                SUM(pgs.blocks) as total_blocks,
                SUM(pgs.turnovers) as total_turnovers,
                SUM(pgs.personal_fouls) as total_personal_fouls
            FROM games g
            LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id AND pgs.team_id = ?
            WHERE g.season = ?
            AND (g.home_team_id = ? OR g.away_team_id = ?)
            AND g.status = 'final'
        """
        results = execute_query(query, [team_id, team_id, season, team_id, team_id])

        if not results or not results[0][0]:
            stats = {
                "team_id": team_id,
                "season": season,
                "games_played": 0,
                "wins": 0,
                "losses": 0,
                "win_pct": 0.0,
            }
        else:
            row = results[0]
            games_played = row[0] or 0
            wins = row[1] or 0
            losses = row[2] or 0
            win_pct = round(wins / games_played, 3) if games_played > 0 else 0.0

            stats = {
                "team_id": team_id,
                "season": season,
                "games_played": games_played,
                "wins": wins,
                "losses": losses,
                "win_pct": win_pct,
                "avg_points_for": round(row[3], 1) if row[3] else 0.0,
                "total_points_for": row[4] or 0,
                "field_goals": {
                    "made": row[5] or 0,
                    "attempted": row[6] or 0,
                    "pct": round(row[5] / row[6], 3) if row[6] else 0.0,
                },
                "three_pointers": {
                    "made": row[7] or 0,
                    "attempted": row[8] or 0,
                    "pct": round(row[7] / row[8], 3) if row[8] else 0.0,
                },
                "free_throws": {
                    "made": row[9] or 0,
                    "attempted": row[10] or 0,
                    "pct": round(row[9] / row[10], 3) if row[10] else 0.0,
                },
                "rebounds": {
                    "offensive": row[11] or 0,
                    "defensive": row[12] or 0,
                    "total": (row[11] or 0) + (row[12] or 0),
                },
                "assists": row[13] or 0,
                "steals": row[14] or 0,
                "blocks": row[15] or 0,
                "turnovers": row[16] or 0,
                "personal_fouls": row[17] or 0,
            }

        if is_htmx_request(request):
            return HTMLResponse(content="")  # Placeholder for team_stats.html

        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team stats: {e}") from e


@router.get("/{team_id}/games", response_model=None)
async def get_team_games(
    request: Request,
    team_id: int,
    season: Annotated[
        int | None, Query(description="Season year (e.g., 2024 for 2023-24 season)", ge=1946)
    ] = None,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Number of games per page", ge=1, le=100)] = 20,
) -> GameListResponse | HTMLResponse:
    """Get a paginated list of games for a specific team.

    Path Parameters:
        team_id: The unique identifier for the team.

    Query Parameters:
        season: Filter games by season year (optional).
        page: Page number for pagination (default: 1).
        page_size: Number of games per page (default: 20, max: 100).

    Returns:
        Paginated list of Game models, or an HTML partial if HTMX request.

    Raises:
        HTTPException: 404 if team not found, 500 if database query fails.
    """
    try:
        # First verify team exists
        team_check = execute_query("SELECT 1 FROM teams WHERE team_id = ?", [team_id])
        if not team_check:
            raise HTTPException(status_code=404, detail=f"Team with ID {team_id} not found")

        # Build count query for pagination
        count_query = """
            SELECT COUNT(*)
            FROM games
            WHERE (home_team_id = ? OR away_team_id = ?)
        """
        count_params: list = [team_id, team_id]

        if season:
            count_query += " AND season = ?"
            count_params.append(season)

        total_result = execute_query(count_query, count_params)
        total = total_result[0][0] if total_result else 0

        # Build data query
        query = """
            SELECT
                game_id,
                season,
                season_type,
                game_date,
                home_team_id,
                away_team_id,
                home_score,
                away_score,
                winner_team_id,
                status
            FROM games
            WHERE (home_team_id = ? OR away_team_id = ?)
        """
        params: list = [team_id, team_id]

        if season:
            query += " AND season = ?"
            params.append(season)

        query += " ORDER BY game_date DESC"
        query += " LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])

        results = execute_query(query, params)

        games = [
            Game(
                **dict(
                    zip(
                        [
                            "game_id",
                            "season",
                            "season_type",
                            "game_date",
                            "home_team_id",
                            "away_team_id",
                            "home_score",
                            "away_score",
                            "winner_team_id",
                            "status",
                        ],
                        row,
                        strict=True,
                    )
                )
            )
            for row in results
        ]

        pages = (total + page_size - 1) // page_size if total > 0 else 0

        response = GameListResponse(
            items=games,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

        if is_htmx_request(request):
            return HTMLResponse(content="")  # Placeholder for game_list.html

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team games: {e}") from e
