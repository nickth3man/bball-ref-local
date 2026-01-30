"""Players API router for basketball player operations.

Provides RESTful endpoints for player profiles, statistics, and game logs.
Supports both JSON API responses and HTMX partial HTML responses.
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.models.player import Player
from app.models.responses import PlayerListResponse
from app.models.stats import PlayerGameStats
from app.services.database import execute_query

router = APIRouter(prefix="/api/v1/players", tags=["players"])


class PlayerSeasonStats(BaseModel):
    """Aggregated player season statistics.

    Attributes:
        season: Season year (e.g., 2024 for 2023-24 season).
        games_played: Number of games played in the season.
        minutes_played: Total minutes played.
        points: Total points scored.
        rebounds_total: Total rebounds.
        assists: Total assists.
        steals: Total steals.
        blocks: Total blocks.
        fg_made: Field goals made.
        fg_attempted: Field goals attempted.
        fg_pct: Field goal percentage (0-1 scale).
        fg3_made: Three-pointers made.
        fg3_attempted: Three-pointers attempted.
        fg3_pct: Three-point percentage (0-1 scale).
        ft_made: Free throws made.
        ft_attempted: Free throws attempted.
        ft_pct: Free throw percentage (0-1 scale).
        turnovers: Total turnovers.
        personal_fouls: Total personal fouls.
    """

    model_config = ConfigDict(from_attributes=True)

    season: int = Field(description="Season year")
    games_played: int = Field(description="Number of games played")
    minutes_played: float = Field(description="Total minutes played")
    points: int = Field(description="Total points")
    rebounds_total: int = Field(description="Total rebounds")
    assists: int = Field(description="Total assists")
    steals: int = Field(description="Total steals")
    blocks: int = Field(description="Total blocks")
    fg_made: int = Field(description="Field goals made")
    fg_attempted: int = Field(description="Field goals attempted")
    fg_pct: float | None = Field(description="Field goal percentage")
    fg3_made: int = Field(description="Three-pointers made")
    fg3_attempted: int = Field(description="Three-pointers attempted")
    fg3_pct: float | None = Field(description="Three-point percentage")
    ft_made: int = Field(description="Free throws made")
    ft_attempted: int = Field(description="Free throws attempted")
    ft_pct: float | None = Field(description="Free throw percentage")
    turnovers: int = Field(description="Total turnovers")
    personal_fouls: int = Field(description="Total personal fouls")


class PlayerStatsResponse(BaseModel):
    """Player statistics response with aggregated and recent game data.

    Attributes:
        player_id: ID of the player.
        career_stats: Aggregated career statistics across all seasons.
        season_stats: List of season-by-season statistics.
        recent_games: List of recent game statistics.
    """

    model_config = ConfigDict(from_attributes=True)

    player_id: int = Field(description="Player ID")
    career_stats: PlayerSeasonStats = Field(description="Career aggregate statistics")
    season_stats: list[PlayerSeasonStats] = Field(description="Season-by-season stats")
    recent_games: list[PlayerGameStats] = Field(description="Recent game statistics")


class PlayerGameLogResponse(BaseModel):
    """Player game log response with pagination.

    Attributes:
        player_id: ID of the player.
        season: Season year for the game log.
        games: List of game statistics.
        total_count: Total number of games in the log.
    """

    model_config = ConfigDict(from_attributes=True)

    player_id: int = Field(description="Player ID")
    season: int | None = Field(description="Season year (None for all seasons)")
    games: list[PlayerGameStats] = Field(description="Game statistics")
    total_count: int = Field(description="Total number of games")


def _is_htmx_request(request: Request) -> bool:
    """Check if request is from HTMX.

    Args:
        request: FastAPI request object.

    Returns:
        True if request has HX-Request header.
    """
    return request.headers.get("HX-Request") == "true"


def _get_templates():
    """Get Jinja2 templates instance from main app."""
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    return Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_model=PlayerListResponse)
async def list_players(
    request: Request,
    search: Annotated[str | None, Query(description="Search by player name")] = None,
    team_id: Annotated[int | None, Query(description="Filter by team ID")] = None,
    position: Annotated[
        str | None, Query(description="Filter by position (PG, SG, SF, PF, C)")
    ] = None,
    page: Annotated[int, Query(description="Page number (1-indexed)", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=100)] = 20,
) -> PlayerListResponse | HTMLResponse:
    """List players with optional filtering and pagination.

    Query Parameters:
        - search: Fuzzy search on player first and last names
        - team_id: Filter players by their current team
        - position: Filter by position (PG, SG, SF, PF, C)
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20, max: 100)

    Returns:
        Paginated list of players. Returns HTML partial if HTMX request.

    Raises:
        HTTPException: 500 if database query fails.
    """
    offset = (page - 1) * page_size

    # Build WHERE clause
    where_clauses = []
    params: list[Any] = []

    if search:
        where_clauses.append("(first_name ILIKE ? OR last_name ILIKE ?)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])

    if team_id is not None:
        where_clauses.append("team_id = ?")
        params.append(team_id)

    if position:
        where_clauses.append("position = ?")
        params.append(position)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Get total count
    count_query = f"SELECT COUNT(*) FROM players WHERE {where_sql}"
    count_result = execute_query(count_query, params if params else None)
    total = count_result[0][0] if count_result else 0

    # Get players
    query = f"""
        SELECT player_id, first_name, last_name, team_id, position, jersey_number,
               height, weight, birth_date, country, draft_year, draft_round, draft_number
        FROM players
        WHERE {where_sql}
        ORDER BY last_name, first_name
        LIMIT ? OFFSET ?
    """
    query_params = params + [page_size, offset]

    try:
        rows = execute_query(query, query_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch players: {e}")

    players = [
        Player(
            player_id=row[0],
            first_name=row[1],
            last_name=row[2],
            team_id=row[3],
            position=row[4],
            jersey_number=row[5],
            height=row[6],
            weight=row[7],
            birth_date=row[8],
            country=row[9],
            draft_year=row[10],
            draft_round=row[11],
            draft_number=row[12],
        )
        for row in rows
    ]

    response_data = PlayerListResponse(
        items=players,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )

    # Return HTML if HTMX request
    if _is_htmx_request(request):
        templates = _get_templates()
        return templates.TemplateResponse(
            "partials/player_list.html",
            {
                "request": request,
                "players": players,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": response_data.pages,
            },
        )

    return response_data


@router.get("/{player_id}", response_model=Player)
async def get_player(
    request: Request,
    player_id: int,
) -> Player | HTMLResponse:
    """Get detailed information for a specific player.

    Path Parameters:
        - player_id: Unique identifier for the player

    Returns:
        Player details including bio, team, and draft information.
        Returns HTML partial (player_card.html) if HTMX request.

    Raises:
        HTTPException: 404 if player not found, 500 if query fails.
    """
    query = """
        SELECT player_id, first_name, last_name, team_id, position, jersey_number,
               height, weight, birth_date, country, draft_year, draft_round, draft_number
        FROM players
        WHERE player_id = ?
    """

    try:
        rows = execute_query(query, [player_id])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch player: {e}")

    if not rows:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

    row = rows[0]
    player = Player(
        player_id=row[0],
        first_name=row[1],
        last_name=row[2],
        team_id=row[3],
        position=row[4],
        jersey_number=row[5],
        height=row[6],
        weight=row[7],
        birth_date=row[8],
        country=row[9],
        draft_year=row[10],
        draft_round=row[11],
        draft_number=row[12],
    )

    # Return HTML if HTMX request
    if _is_htmx_request(request):
        templates = _get_templates()
        return templates.TemplateResponse(
            "partials/player_card.html", {"request": request, "player": player}
        )

    return player


@router.get("/{player_id}/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    request: Request,
    player_id: int,
    season: Annotated[int | None, Query(description="Specific season year (optional)")] = None,
) -> PlayerStatsResponse | HTMLResponse:
    """Get player statistics including career totals and recent games.

    Path Parameters:
        - player_id: Unique identifier for the player

    Query Parameters:
        - season: Filter to specific season year (optional)

    Returns:
        Aggregated career stats, season-by-season breakdown, and recent games.
        Returns HTML partial (stats_table.html) if HTMX request.

    Raises:
        HTTPException: 404 if player not found, 500 if query fails.
    """
    # First verify player exists
    player_check = execute_query("SELECT player_id FROM players WHERE player_id = ?", [player_id])
    if not player_check:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

    # Build season filter
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

    # Get career aggregate stats from game logs
    career_query = f"""
        SELECT 
            COUNT(*) as games_played,
            COALESCE(SUM(minutes_played), 0) as minutes,
            SUM(points) as points,
            SUM(rebounds_offensive + rebounds_defensive) as rebounds,
            SUM(assists) as assists,
            SUM(steals) as steals,
            SUM(blocks) as blocks,
            SUM(fg_made) as fg_made,
            SUM(fg_attempted) as fg_attempted,
            SUM(fg3_made) as fg3_made,
            SUM(fg3_attempted) as fg3_attempted,
            SUM(ft_made) as ft_made,
            SUM(ft_attempted) as ft_attempted,
            SUM(turnovers) as turnovers,
            SUM(personal_fouls) as fouls
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ? {season_filter}
    """

    try:
        career_row = execute_query(career_query, params)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch career stats: {e}")

    # Calculate percentages
    fg_attempted = career_row[8] or 0
    fg3_attempted = career_row[10] or 0
    ft_attempted = career_row[12] or 0

    career_stats = PlayerSeasonStats(
        season=season or 0,
        games_played=career_row[0] or 0,
        minutes_played=career_row[1] or 0,
        points=career_row[2] or 0,
        rebounds_total=career_row[3] or 0,
        assists=career_row[4] or 0,
        steals=career_row[5] or 0,
        blocks=career_row[6] or 0,
        fg_made=career_row[7] or 0,
        fg_attempted=fg_attempted,
        fg_pct=round(career_row[7] / fg_attempted, 3) if fg_attempted > 0 else None,
        fg3_made=career_row[9] or 0,
        fg3_attempted=fg3_attempted,
        fg3_pct=round(career_row[9] / fg3_attempted, 3) if fg3_attempted > 0 else None,
        ft_made=career_row[11] or 0,
        ft_attempted=ft_attempted,
        ft_pct=round(career_row[11] / ft_attempted, 3) if ft_attempted > 0 else None,
        turnovers=career_row[13] or 0,
        personal_fouls=career_row[14] or 0,
    )

    # Get season-by-season stats (if no season filter)
    season_stats = []
    if not season:
        season_query = """
            SELECT 
                g.season,
                COUNT(*) as games_played,
                COALESCE(SUM(minutes_played), 0) as minutes,
                SUM(points) as points,
                SUM(rebounds_offensive + rebounds_defensive) as rebounds,
                SUM(assists) as assists,
                SUM(steals) as steals,
                SUM(blocks) as blocks,
                SUM(fg_made) as fg_made,
                SUM(fg_attempted) as fg_attempted,
                SUM(fg3_made) as fg3_made,
                SUM(fg3_attempted) as fg3_attempted,
                SUM(ft_made) as ft_made,
                SUM(ft_attempted) as ft_attempted,
                SUM(turnovers) as turnovers,
                SUM(personal_fouls) as fouls
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.player_id = ?
            GROUP BY g.season
            ORDER BY g.season DESC
        """

        try:
            season_rows = execute_query(season_query, [player_id])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch season stats: {e}")

        for row in season_rows:
            fg_att = row[9] or 0
            fg3_att = row[11] or 0
            ft_att = row[13] or 0

            season_stats.append(
                PlayerSeasonStats(
                    season=row[0],
                    games_played=row[1] or 0,
                    minutes_played=row[2] or 0,
                    points=row[3] or 0,
                    rebounds_total=row[4] or 0,
                    assists=row[5] or 0,
                    steals=row[6] or 0,
                    blocks=row[7] or 0,
                    fg_made=row[8] or 0,
                    fg_attempted=fg_att,
                    fg_pct=round(row[8] / fg_att, 3) if fg_att > 0 else None,
                    fg3_made=row[10] or 0,
                    fg3_attempted=fg3_att,
                    fg3_pct=round(row[10] / fg3_att, 3) if fg3_att > 0 else None,
                    ft_made=row[12] or 0,
                    ft_attempted=ft_att,
                    ft_pct=round(row[12] / ft_att, 3) if ft_att > 0 else None,
                    turnovers=row[14] or 0,
                    personal_fouls=row[15] or 0,
                )
            )

    # Get recent games
    recent_query = f"""
        SELECT 
            stat_id, pgs.game_id, player_id, pgs.team_id, minutes_played, points,
            rebounds_offensive, rebounds_defensive, assists, steals, blocks,
            turnovers, personal_fouls, fg_made, fg_attempted, fg3_made, fg3_attempted,
            ft_made, ft_attempted
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE player_id = ? {season_filter}
        ORDER BY g.game_date DESC
        LIMIT 10
    """

    try:
        recent_rows = execute_query(recent_query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent games: {e}")

    recent_games = [
        PlayerGameStats(
            stat_id=row[0],
            game_id=row[1],
            player_id=row[2],
            team_id=row[3],
            minutes_played=row[4],
            points=row[5],
            rebounds_offensive=row[6],
            rebounds_defensive=row[7],
            assists=row[8],
            steals=row[9],
            blocks=row[10],
            turnovers=row[11],
            personal_fouls=row[12],
            fg_made=row[13],
            fg_attempted=row[14],
            fg3_made=row[15],
            fg3_attempted=row[16],
            ft_made=row[17],
            ft_attempted=row[18],
        )
        for row in recent_rows
    ]

    response_data = PlayerStatsResponse(
        player_id=player_id,
        career_stats=career_stats,
        season_stats=season_stats,
        recent_games=recent_games,
    )

    # Return HTML if HTMX request
    if _is_htmx_request(request):
        templates = _get_templates()
        return templates.TemplateResponse(
            "partials/stats_table.html",
            {
                "request": request,
                "player_id": player_id,
                "career_stats": career_stats,
                "season_stats": season_stats,
                "recent_games": recent_games,
            },
        )

    return response_data


@router.get("/{player_id}/games", response_model=PlayerGameLogResponse)
async def get_player_games(
    request: Request,
    player_id: int,
    season: Annotated[int | None, Query(description="Filter by season year")] = None,
    limit: Annotated[int, Query(description="Maximum games to return", ge=1, le=500)] = 100,
) -> PlayerGameLogResponse | HTMLResponse:
    """Get player game log with optional season filtering.

    Path Parameters:
        - player_id: Unique identifier for the player

    Query Parameters:
        - season: Filter to specific season (optional)
        - limit: Maximum number of games to return (default: 100, max: 500)

    Returns:
        List of game statistics for the player.
        Returns HTML partial (game_log_table.html) if HTMX request.

    Raises:
        HTTPException: 404 if player not found, 500 if query fails.
    """
    # First verify player exists
    player_check = execute_query("SELECT player_id FROM players WHERE player_id = ?", [player_id])
    if not player_check:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

    # Build season filter
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

    # Get total count
    count_query = f"""
        SELECT COUNT(*) 
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ? {season_filter}
    """

    try:
        total_result = execute_query(count_query, params)
        total_count = total_result[0][0] if total_result else 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to count games: {e}")

    # Get games
    query = f"""
        SELECT 
            stat_id, pgs.game_id, player_id, pgs.team_id, minutes_played, points,
            rebounds_offensive, rebounds_defensive, assists, steals, blocks,
            turnovers, personal_fouls, fg_made, fg_attempted, fg3_made, fg3_attempted,
            ft_made, ft_attempted, g.game_date, g.season
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE player_id = ? {season_filter}
        ORDER BY g.game_date DESC
        LIMIT ?
    """
    query_params = params + [limit]

    try:
        rows = execute_query(query, query_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch games: {e}")

    games = [
        PlayerGameStats(
            stat_id=row[0],
            game_id=row[1],
            player_id=row[2],
            team_id=row[3],
            minutes_played=row[4],
            points=row[5],
            rebounds_offensive=row[6],
            rebounds_defensive=row[7],
            assists=row[8],
            steals=row[9],
            blocks=row[10],
            turnovers=row[11],
            personal_fouls=row[12],
            fg_made=row[13],
            fg_attempted=row[14],
            fg3_made=row[15],
            fg3_attempted=row[16],
            ft_made=row[17],
            ft_attempted=row[18],
        )
        for row in rows
    ]

    response_data = PlayerGameLogResponse(
        player_id=player_id,
        season=season,
        games=games,
        total_count=total_count,
    )

    # Return HTML if HTMX request
    if _is_htmx_request(request):
        templates = _get_templates()
        return templates.TemplateResponse(
            "partials/game_log_table.html",
            {
                "request": request,
                "player_id": player_id,
                "games": games,
                "season": season,
                "total_count": total_count,
            },
        )

    return response_data
