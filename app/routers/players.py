"""Players API router for basketball player operations.

Provides RESTful endpoints for player profiles, statistics, and game logs.
Supports both JSON API responses and HTMX partial HTML responses.
"""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.models.player import Player
from app.models.responses import PlayerListResponse
from app.models.stats import PlayerGameStats
from app.services.database import execute_query
from app.services.export_service import export_game_logs, export_player_stats
from app.services.htmx_utils import get_templates, is_htmx_request

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


def _build_player_from_row(row: tuple) -> Player:
    """Build a Player model from a database row.

    Args:
        row: Database row tuple with player data.

    Returns:
        Populated Player instance.
    """
    return Player(
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


def _build_stats_from_row(row: tuple) -> PlayerSeasonStats:
    """Build PlayerSeasonStats from a database row with percentage calculations.

    Args:
        row: Database row with season statistics.

    Returns:
        Populated PlayerSeasonStats instance.
    """
    fg_attempted = row[9] or 0
    fg3_attempted = row[11] or 0
    ft_attempted = row[13] or 0

    return PlayerSeasonStats(
        season=row[0],
        games_played=row[1] or 0,
        minutes_played=row[2] or 0,
        points=row[3] or 0,
        rebounds_total=row[4] or 0,
        assists=row[5] or 0,
        steals=row[6] or 0,
        blocks=row[7] or 0,
        fg_made=row[8] or 0,
        fg_attempted=fg_attempted,
        fg_pct=round(row[8] / fg_attempted, 3) if fg_attempted > 0 else None,
        fg3_made=row[10] or 0,
        fg3_attempted=fg3_attempted,
        fg3_pct=round(row[10] / fg3_attempted, 3) if fg3_attempted > 0 else None,
        ft_made=row[12] or 0,
        ft_attempted=ft_attempted,
        ft_pct=round(row[12] / ft_attempted, 3) if ft_attempted > 0 else None,
        turnovers=row[14] or 0,
        personal_fouls=row[15] or 0,
    )


def _get_career_stats(player_id: int, season: int | None) -> PlayerSeasonStats:
    """Fetch and calculate career statistics for a player.

    Args:
        player_id: The player's unique identifier.
        season: Optional season filter.

    Returns:
        PlayerSeasonStats with career aggregates.

    Raises:
        HTTPException: If database query fails.
    """
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

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
        raise HTTPException(status_code=500, detail=f"Failed to fetch career stats: {e}") from e

    fg_attempted = career_row[8] or 0
    fg3_attempted = career_row[10] or 0
    ft_attempted = career_row[12] or 0

    return PlayerSeasonStats(
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


def _get_season_stats(player_id: int) -> list[PlayerSeasonStats]:
    """Fetch season-by-season statistics for a player.

    Args:
        player_id: The player's unique identifier.

    Returns:
        List of PlayerSeasonStats for each season.

    Raises:
        HTTPException: If database query fails.
    """
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch season stats: {e}") from e

    return [_build_stats_from_row(row) for row in season_rows]


def _get_recent_games(player_id: int, season: int | None, limit: int = 10) -> list[PlayerGameStats]:
    """Fetch recent games for a player.

    Args:
        player_id: The player's unique identifier.
        season: Optional season filter.
        limit: Maximum number of games to return.

    Returns:
        List of PlayerGameStats for recent games.

    Raises:
        HTTPException: If database query fails.
    """
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

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
        LIMIT ?
    """
    query_params = params + [limit]

    try:
        recent_rows = execute_query(recent_query, query_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent games: {e}") from e

    return [
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

    # Single query with window function for count
    query = f"""
        SELECT
            player_id, first_name, last_name, team_id, position, jersey_number,
            height, weight, birth_date, country, draft_year, draft_round, draft_number,
            COUNT(*) OVER() as total_count
        FROM players
        WHERE {where_sql}
        ORDER BY last_name, first_name
        LIMIT ? OFFSET ?
    """
    query_params = params + [page_size, offset]

    try:
        rows = execute_query(query, query_params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch players: {e}") from e

    total = rows[0][-1] if rows else 0
    players = [_build_player_from_row(row[:-1]) for row in rows]

    response_data = PlayerListResponse(
        items=players,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )

    # Return HTML if HTMX request
    if is_htmx_request(request):
        templates = get_templates()
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch player: {e}") from e

    if not rows:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

    row = rows[0]
    player = _build_player_from_row(row)

    # Return HTML if HTMX request
    if is_htmx_request(request):
        templates = get_templates()
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
    # Fetch all stats components using helper functions
    # Player existence is handled naturally - empty stats indicate player not found
    career_stats = _get_career_stats(player_id, season)
    season_stats = _get_season_stats(player_id) if not season else []
    recent_games = _get_recent_games(player_id, season, limit=10)

    response_data = PlayerStatsResponse(
        player_id=player_id,
        career_stats=career_stats,
        season_stats=season_stats,
        recent_games=recent_games,
    )

    # Return HTML if HTMX request
    if is_htmx_request(request):
        templates = get_templates()
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
        HTTPException: 500 if query fails.
    """
    # Build season filter
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

    # Single query with window function for count
    query = f"""
        SELECT
            stat_id, pgs.game_id, player_id, pgs.team_id, minutes_played, points,
            rebounds_offensive, rebounds_defensive, assists, steals, blocks,
            turnovers, personal_fouls, fg_made, fg_attempted, fg3_made, fg3_attempted,
            ft_made, ft_attempted, g.game_date, g.season,
            COUNT(*) OVER() as total_count
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
        raise HTTPException(status_code=500, detail=f"Failed to fetch games: {e}") from e

    total_count = rows[0][-1] if rows else 0

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
    if is_htmx_request(request):
        templates = get_templates()
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


@router.get("/{player_id}/gamelog/{year}", response_model=None)
async def get_player_gamelog_enhanced(
    request: Request,
    player_id: str,
    year: int,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[
        int | str, Query(description="Items per page (50, 100, 200, or 'all')")
    ] = 50,
    sort_by: Annotated[
        str, Query(description="Column to sort by")
    ] = "game_date",
    sort_order: Annotated[
        str, Query(description="Sort order (asc or desc)")
    ] = "desc",
    home_away: Annotated[
        str, Query(description="Filter by home/away (home, away, all)")
    ] = "all",
    result: Annotated[
        str, Query(description="Filter by result (win, loss, all)")
    ] = "all",
) -> HTMLResponse:
    """Get enhanced player game log with sorting, pagination, and filtering.

    Path Parameters:
        - player_id: Unique identifier for the player
        - year: Season year for the game log

    Query Parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (50, 100, 200, or 'all')
        - sort_by: Column to sort by (game_date, points, rebounds, assists, etc.)
        - sort_order: Sort order (asc or desc)
        - home_away: Filter by home/away (home, away, all)
        - result: Filter by result (win, loss, all)

    Returns:
        HTML partial with game log table.
    """
    templates = get_templates()

    # Validate and convert page_size
    if isinstance(page_size, str) and page_size.lower() == "all":
        limit_clause = ""
        offset_clause = ""
        params: list[Any] = [player_id, year]
    else:
        try:
            page_size_int = int(page_size)
            if page_size_int not in [50, 100, 200]:
                page_size_int = 50
        except (ValueError, TypeError):
            page_size_int = 50

        offset = (page - 1) * page_size_int
        limit_clause = f"LIMIT {page_size_int}"
        offset_clause = f"OFFSET {offset}"
        params = [player_id, year]

    # Validate sort_by column
    valid_sort_columns = {
        "game_date": "g.game_date",
        "points": "pgs.points",
        "rebounds": "(pgs.rebounds_offensive + pgs.rebounds_defensive)",
        "assists": "pgs.assists",
        "steals": "pgs.steals",
        "blocks": "pgs.blocks",
        "minutes": "pgs.minutes_played",
        "fg_pct": "CASE WHEN pgs.fg_attempted > 0 THEN pgs.fg_made::FLOAT / pgs.fg_attempted ELSE 0 END",
    }
    sort_column = valid_sort_columns.get(sort_by, "g.game_date")

    # Validate sort_order
    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

    # Build filter conditions
    filter_conditions = []
    if home_away.lower() == "home":
        filter_conditions.append("AND pgs.team_id = g.home_team_id")
    elif home_away.lower() == "away":
        filter_conditions.append("AND pgs.team_id = g.away_team_id")

    if result.lower() == "win":
        filter_conditions.append("""
            AND ((pgs.team_id = g.home_team_id AND g.home_score > g.away_score)
                 OR (pgs.team_id = g.away_team_id AND g.away_score > g.home_score))
        """)
    elif result.lower() == "loss":
        filter_conditions.append("""
            AND ((pgs.team_id = g.home_team_id AND g.home_score < g.away_score)
                 OR (pgs.team_id = g.away_team_id AND g.away_score < g.home_score))
        """)

    filter_sql = " ".join(filter_conditions)

    # Get total count with filters
    count_query = f"""
        SELECT COUNT(*)
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ? AND g.season = ?
        {filter_sql}
    """

    try:
        count_result = execute_query(count_query, params)
        total_count = count_result[0][0] if count_result else 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to count games: {e}") from e

    # Main query with sorting and pagination
    query = f"""
        SELECT
            g.game_date,
            g.season,
            ht.abbreviation as opponent_abbr,
            ht.team_id as opponent_id,
            CASE WHEN pgs.team_id = g.home_team_id THEN 1 ELSE 0 END as is_home,
            CASE
                WHEN (pgs.team_id = g.home_team_id AND g.home_score > g.away_score)
                     OR (pgs.team_id = g.away_team_id AND g.away_score > g.home_score)
                THEN 1 ELSE 0
            END as is_win,
            CASE WHEN pgs.team_id = g.home_team_id THEN g.home_score ELSE g.away_score END as team_score,
            CASE WHEN pgs.team_id = g.home_team_id THEN g.away_score ELSE g.home_score END as opponent_score,
            pgs.minutes_played,
            pgs.points,
            pgs.rebounds_offensive + pgs.rebounds_defensive as rebounds_total,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.fg_made,
            pgs.fg_attempted,
            pgs.fg3_made,
            pgs.fg3_attempted,
            pgs.ft_made,
            pgs.ft_attempted,
            pgs.turnovers,
            pgs.personal_fouls
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        LEFT JOIN teams ht ON CASE
            WHEN pgs.team_id = g.home_team_id THEN g.away_team_id
            ELSE g.home_team_id
        END = ht.team_id
        WHERE pgs.player_id = ? AND g.season = ?
        {filter_sql}
        ORDER BY {sort_column} {sort_direction}
        {limit_clause}
        {offset_clause}
    """

    try:
        rows = execute_query(query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch games: {e}") from e

    # Calculate pagination
    page_size_int = total_count if isinstance(page_size, str) and page_size.lower() == "all" else int(page_size) if isinstance(page_size, int) else 50
    total_pages = (total_count + page_size_int - 1) // page_size_int if page_size_int > 0 else 1

    games = []
    for row in rows:
        games.append({
            "game_date": row[0],
            "season": row[1],
            "opponent_abbreviation": row[2],
            "opponent_id": row[3],
            "is_home": bool(row[4]),
            "is_win": bool(row[5]),
            "team_score": row[6],
            "opponent_score": row[7],
            "minutes_played": row[8],
            "points": row[9],
            "rebounds_total": row[10],
            "assists": row[11],
            "steals": row[12],
            "blocks": row[13],
            "fg_made": row[14],
            "fg_attempted": row[15],
            "fg3_made": row[16],
            "fg3_attempted": row[17],
            "ft_made": row[18],
            "ft_attempted": row[19],
            "turnovers": row[20],
            "personal_fouls": row[21],
        })

    return templates.TemplateResponse(
        "partials/player_game_log.html",
        {
            "request": request,
            "player_id": player_id,
            "games": games,
            "season": year,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "home_away": home_away,
            "result": result,
        },
    )


@router.get("/{player_id}/export")
async def export_player_data(
    player_id: str,
    format: Annotated[str, Query(description="Export format (csv or json)")] = "csv",
    type: Annotated[str, Query(description="Export type (stats, games, all)")] = "all",
    season: Annotated[int | None, Query(description="Season filter for games")] = None,
) -> Response:
    """Export player data to CSV or JSON.

    Path Parameters:
        - player_id: Unique identifier for the player

    Query Parameters:
        - format: Export format ('csv' or 'json')
        - type: Export type ('stats', 'games', or 'all')
        - season: Optional season filter for games export

    Returns:
        CSV or JSON file download response.
    """
    format_type = format.lower()
    if format_type not in ["csv", "json"]:
        format_type = "csv"

    export_type = type.lower()

    if export_type == "stats":
        return export_player_stats(player_id, format_type)
    
    if export_type == "games":
        return export_game_logs(player_id, season, format_type)

    # Default to stats for now (could combine both in future)
    return export_player_stats(player_id, format_type)


@router.get("/index", response_model=None)
async def get_player_index(
    request: Request,
    letter: Annotated[str | None, Query(description="Filter by first letter of last name (A-Z)")] = None,
) -> HTMLResponse:
    """Get alphabetical player index with A-Z navigation.

    Query Parameters:
        - letter: Filter players by first letter of last name (A-Z)

    Returns:
        HTML partial with player index organized alphabetically.
    """
    templates = get_templates()

    # Validate letter parameter
    if letter:
        letter = letter.upper()
        if len(letter) != 1 or not letter.isalpha():
            letter = None

    # Build query
    where_clause = ""
    params: list[Any] = []
    if letter:
        where_clause = "WHERE UPPER(SUBSTRING(last_name, 1, 1)) = ?"
        params.append(letter)

    query = f"""
        SELECT
            player_id,
            first_name,
            last_name,
            full_name,
            team_id,
            position,
            draft_year,
            active
        FROM players
        {where_clause}
        ORDER BY last_name, first_name
    """

    try:
        rows = execute_query(query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch player index: {e}") from e

    # Organize players by first letter of last name
    players_by_letter: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        player = {
            "player_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "full_name": row[3],
            "team_id": row[4],
            "position": row[5],
            "draft_year": row[6],
            "active": row[7],
        }
        first_letter = player["last_name"][0].upper() if player["last_name"] else "#"
        if first_letter not in players_by_letter:
            players_by_letter[first_letter] = []
        players_by_letter[first_letter].append(player)

    # Get count of players per letter
    count_query = """
        SELECT UPPER(SUBSTRING(last_name, 1, 1)) as letter, COUNT(*) as count
        FROM players
        GROUP BY UPPER(SUBSTRING(last_name, 1, 1))
        ORDER BY letter
    """
    try:
        count_rows = execute_query(count_query, [])
        letter_counts = {row[0]: row[1] for row in count_rows}
    except Exception:
        letter_counts = {}

    # Get all letters that have players
    available_letters = sorted(letter_counts.keys())

    return templates.TemplateResponse(
        "players/index.html",
        {
            "request": request,
            "players_by_letter": players_by_letter,
            "letter_counts": letter_counts,
            "available_letters": available_letters,
            "selected_letter": letter,
        },
    )
