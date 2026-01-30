"""Games API router for basketball game data.

Provides endpoints for listing games, retrieving today's games,
and fetching detailed box score information.
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from app.models import Game, PlayerGameStats, Team
from app.services.database import execute_query
from app.services.htmx_utils import is_htmx_request

router = APIRouter(
    prefix="/api/v1/games",
    tags=["games"],
)


def _row_to_game(row: tuple) -> Game:
    """Convert a database row to a Game model.

    Args:
        row: Database row tuple from games table query.

    Returns:
        Game: Populated Game model instance.
    """
    return Game(
        game_id=row[0],
        season=row[1],
        season_type=row[2],
        game_date=row[3],
        home_team_id=row[4],
        away_team_id=row[5],
        home_score=row[6],
        away_score=row[7],
        winner_team_id=row[8],
        status=row[9],
    )


def _row_to_player_stats(row: tuple) -> PlayerGameStats:
    """Convert a database row to a PlayerGameStats model.

    Args:
        row: Database row tuple from player_game_stats table query.

    Returns:
        PlayerGameStats: Populated PlayerGameStats model instance.
    """
    return PlayerGameStats(
        stat_id=row[0],
        game_id=row[1],
        player_id=row[2],
        team_id=row[3],
        minutes_played=row[4],
        points=row[5] or 0,
        rebounds_offensive=row[6] or 0,
        rebounds_defensive=row[7] or 0,
        assists=row[8] or 0,
        steals=row[9] or 0,
        blocks=row[10] or 0,
        turnovers=row[11] or 0,
        personal_fouls=row[12] or 0,
        fg_made=row[13] or 0,
        fg_attempted=row[14] or 0,
        fg3_made=row[15] or 0,
        fg3_attempted=row[16] or 0,
        ft_made=row[17] or 0,
        ft_attempted=row[18] or 0,
    )


def _row_to_team(row: tuple) -> Team:
    """Convert a database row to a Team model.

    Args:
        row: Database row tuple from teams table query.

    Returns:
        Team: Populated Team model instance.
    """
    return Team(
        team_id=row[0],
        full_name=row[1],
        abbreviation=row[2],
        nickname=row[3],
        city=row[4],
        state=row[5],
        year_founded=row[6],
        arena=row[7],
        owner=row[8],
        general_manager=row[9],
        head_coach=row[10],
        conference=row[11],
        division=row[12],
    )


def _aggregate_stats(player_stats: list[PlayerGameStats]) -> dict[str, Any]:
    """Aggregate player statistics into team totals.

    Args:
        player_stats: List of PlayerGameStats for a team.

    Returns:
        Dictionary containing aggregated team statistics.
    """
    totals = {
        "minutes_played": 0.0,
        "points": 0,
        "rebounds_offensive": 0,
        "rebounds_defensive": 0,
        "rebounds_total": 0,
        "assists": 0,
        "steals": 0,
        "blocks": 0,
        "turnovers": 0,
        "personal_fouls": 0,
        "fg_made": 0,
        "fg_attempted": 0,
        "fg3_made": 0,
        "fg3_attempted": 0,
        "ft_made": 0,
        "ft_attempted": 0,
    }

    for stats in player_stats:
        if stats.minutes_played:
            totals["minutes_played"] += stats.minutes_played
        totals["points"] += stats.points
        totals["rebounds_offensive"] += stats.rebounds_offensive
        totals["rebounds_defensive"] += stats.rebounds_defensive
        totals["rebounds_total"] += stats.rebounds_total
        totals["assists"] += stats.assists
        totals["steals"] += stats.steals
        totals["blocks"] += stats.blocks
        totals["turnovers"] += stats.turnovers
        totals["personal_fouls"] += stats.personal_fouls
        totals["fg_made"] += stats.fg_made
        totals["fg_attempted"] += stats.fg_attempted
        totals["fg3_made"] += stats.fg3_made
        totals["fg3_attempted"] += stats.fg3_attempted
        totals["ft_made"] += stats.ft_made
        totals["ft_attempted"] += stats.ft_attempted

    # Calculate percentages
    if totals["fg_attempted"] > 0:
        totals["fg_pct"] = round(totals["fg_made"] / totals["fg_attempted"], 3)
    else:
        totals["fg_pct"] = None

    if totals["fg3_attempted"] > 0:
        totals["fg3_pct"] = round(totals["fg3_made"] / totals["fg3_attempted"], 3)
    else:
        totals["fg3_pct"] = None

    if totals["ft_attempted"] > 0:
        totals["ft_pct"] = round(totals["ft_made"] / totals["ft_attempted"], 3)
    else:
        totals["ft_pct"] = None

    return totals


@router.get("/", response_model=None)
async def list_games(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    team_id: int | None = None,
    season: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any] | HTMLResponse:
    """List games with optional filters and pagination.

    Query Parameters:
        date_from: Start date filter (YYYY-MM-DD format)
        date_to: End date filter (YYYY-MM-DD format)
        team_id: Filter by team ID
        season: Filter by season year
        page: Page number (default: 1)
        page_size: Items per page (default: 20, max: 100)

    Returns:
        Paginated list of games (JSON or HTML partial for HTMX requests)

    Raises:
        HTTPException: If database query fails
    """
    # Build query dynamically based on filters
    where_clauses = []
    params: list[Any] = []

    if date_from:
        where_clauses.append("game_date >= ?")
        params.append(date_from)

    if date_to:
        where_clauses.append("game_date <= ?")
        params.append(date_to)

    if team_id:
        where_clauses.append("(home_team_id = ? OR away_team_id = ?)")
        params.extend([team_id, team_id])

    if season:
        where_clauses.append("season = ?")
        params.append(season)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Count total for pagination
    count_query = f"SELECT COUNT(*) FROM games WHERE {where_sql}"
    count_result = execute_query(count_query, params if params else None)
    total_count = count_result[0][0] if count_result else 0

    # Get games with pagination
    offset = (page - 1) * page_size
    query = f"""
        SELECT game_id, season, season_type, game_date, home_team_id, away_team_id,
               home_score, away_score, winner_team_id, status
        FROM games
        WHERE {where_sql}
        ORDER BY game_date DESC, game_id DESC
        LIMIT ? OFFSET ?
    """
    query_params = params + [page_size, offset]
    rows = execute_query(query, query_params)

    games = [_row_to_game(row) for row in rows]

    # Calculate pagination metadata
    total_pages = (total_count + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1

    response_data = {
        "games": [game.model_dump() for game in games],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    }

    # Check for HTMX request
    if is_htmx_request(request):
        return HTMLResponse(
            content=f"<!-- game_list.html partial would render {len(games)} games -->"
        )

    return response_data


@router.get("/today", response_model=None)
async def get_todays_games(request: Request) -> dict[str, Any] | HTMLResponse:
    """Get all games scheduled for today.

    Returns:
        List of today's games (JSON or HTML partial for HTMX requests)

    Raises:
        HTTPException: If database query fails
    """
    today = date.today()

    query = """
        SELECT game_id, season, season_type, game_date, home_team_id, away_team_id,
               home_score, away_score, winner_team_id, status
        FROM games
        WHERE game_date = ?
        ORDER BY game_id
    """
    rows = execute_query(query, [today])

    games = [_row_to_game(row) for row in rows]

    response_data = {
        "date": today.isoformat(),
        "games": [game.model_dump() for game in games],
        "count": len(games),
    }

    # Check for HTMX request
    if is_htmx_request(request):
        return HTMLResponse(
            content=f"<!-- game_list.html partial would render {len(games)} games for today -->"
        )

    return response_data


@router.get("/{game_id}", response_model=None)
async def get_game_box_score(
    request: Request,
    game_id: str,
) -> dict[str, Any] | HTMLResponse:
    """Get detailed box score for a specific game.

    Path Parameters:
        game_id: Unique identifier for the game (e.g., "0022400001")

    Returns:
        Game details with home/away team info and player statistics
        (JSON or HTML partial for HTMX requests)

    Raises:
        HTTPException: 404 if game not found
    """
    # Get game details
    game_query = """
        SELECT game_id, season, season_type, game_date, home_team_id, away_team_id,
               home_score, away_score, winner_team_id, status
        FROM games
        WHERE game_id = ?
    """
    game_rows = execute_query(game_query, [game_id])

    if not game_rows:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

    game = _row_to_game(game_rows[0])

    # Get team details
    teams_query = """
        SELECT team_id, full_name, abbreviation, nickname, city, state,
               year_founded, arena, owner, general_manager, head_coach,
               conference, division
        FROM teams
        WHERE team_id IN (?, ?)
    """
    team_rows = execute_query(teams_query, [game.home_team_id, game.away_team_id])

    teams_by_id: dict[int, Team] = {}
    for row in team_rows:
        team = _row_to_team(row)
        teams_by_id[team.team_id] = team

    home_team = teams_by_id.get(game.home_team_id)
    away_team = teams_by_id.get(game.away_team_id)

    # Get player statistics for this game
    stats_query = """
        SELECT stat_id, game_id, player_id, team_id, minutes_played, points,
               rebounds_offensive, rebounds_defensive, assists, steals, blocks,
               turnovers, personal_fouls, fg_made, fg_attempted, fg3_made,
               fg3_attempted, ft_made, ft_attempted
        FROM player_game_stats
        WHERE game_id = ?
        ORDER BY team_id, points DESC, minutes_played DESC
    """
    stats_rows = execute_query(stats_query, [game_id])

    home_players: list[PlayerGameStats] = []
    away_players: list[PlayerGameStats] = []

    for row in stats_rows:
        stats = _row_to_player_stats(row)
        if stats.team_id == game.home_team_id:
            home_players.append(stats)
        elif stats.team_id == game.away_team_id:
            away_players.append(stats)

    # Aggregate team totals
    home_totals = _aggregate_stats(home_players)
    away_totals = _aggregate_stats(away_players)

    response_data = {
        "game": game.model_dump(),
        "home_team": home_team.model_dump() if home_team else None,
        "away_team": away_team.model_dump() if away_team else None,
        "home_players": [p.model_dump() for p in home_players],
        "away_players": [p.model_dump() for p in away_players],
        "home_totals": home_totals,
        "away_totals": away_totals,
    }

    # Check for HTMX request
    if is_htmx_request(request):
        return HTMLResponse(content=f"<!-- box_score.html partial would render game {game_id} -->")

    return response_data
