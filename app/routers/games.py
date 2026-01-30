"""Games API router for basketball game data.

Provides endpoints for listing games, retrieving today's games,
and fetching detailed box score information.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from app.models import Game, PlayerGameStats, Team
from app.services.database import execute_query
from app.services.export_service import export_box_score
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

    # Get games with pagination using window function for count
    offset = (page - 1) * page_size
    query = f"""
        SELECT
            game_id, season, season_type, game_date, home_team_id, away_team_id,
            home_score, away_score, winner_team_id, status,
            COUNT(*) OVER() as total_count
        FROM games
        WHERE {where_sql}
        ORDER BY game_date DESC, game_id DESC
        LIMIT ? OFFSET ?
    """
    query_params = params + [page_size, offset]
    rows = execute_query(query, query_params)

    total_count = rows[0][-1] if rows else 0
    games = [_row_to_game(row[:-1]) for row in rows]  # Exclude total_count

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
    # Single query combining game, teams, and player stats using LEFT JOINs
    box_score_query = """
        SELECT
            g.game_id, g.season, g.season_type, g.game_date,
            g.home_team_id, g.away_team_id, g.home_score, g.away_score,
            g.winner_team_id, g.status,
            ht.team_id as ht_id, ht.full_name as ht_name, ht.abbreviation as ht_abbrev,
            ht.nickname as ht_nickname, ht.city as ht_city, ht.state as ht_state,
            ht.year_founded as ht_year, ht.arena as ht_arena, ht.owner as ht_owner,
            ht.general_manager as ht_gm, ht.head_coach as ht_coach,
            ht.conference as ht_conf, ht.division as ht_div,
            at.team_id as at_id, at.full_name as at_name, at.abbreviation as at_abbrev,
            at.nickname as at_nickname, at.city as at_city, at.state as at_state,
            at.year_founded as at_year, at.arena as at_arena, at.owner as at_owner,
            at.general_manager as at_gm, at.head_coach as at_coach,
            at.conference as at_conf, at.division as at_div,
            pgs.stat_id, pgs.player_id, pgs.team_id as pgs_team_id,
            pgs.minutes_played, pgs.points, pgs.rebounds_offensive,
            pgs.rebounds_defensive, pgs.assists, pgs.steals, pgs.blocks,
            pgs.turnovers, pgs.personal_fouls, pgs.fg_made, pgs.fg_attempted,
            pgs.fg3_made, pgs.fg3_attempted, pgs.ft_made, pgs.ft_attempted
        FROM games g
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id
        LEFT JOIN teams at ON g.away_team_id = at.team_id
        LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id
        WHERE g.game_id = ?
        ORDER BY pgs.team_id, pgs.points DESC, pgs.minutes_played DESC
    """
    rows = execute_query(box_score_query, [game_id])

    if not rows:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

    # Extract game data from first row
    first_row = rows[0]
    game = Game(
        game_id=first_row[0],
        season=first_row[1],
        season_type=first_row[2],
        game_date=first_row[3],
        home_team_id=first_row[4],
        away_team_id=first_row[5],
        home_score=first_row[6],
        away_score=first_row[7],
        winner_team_id=first_row[8],
        status=first_row[9],
    )

    # Extract team data (same in all rows)
    home_team = (
        Team(
            team_id=first_row[10],
            full_name=first_row[11],
            abbreviation=first_row[12],
            nickname=first_row[13],
            city=first_row[14],
            state=first_row[15],
            year_founded=first_row[16],
            arena=first_row[17],
            owner=first_row[18],
            general_manager=first_row[19],
            head_coach=first_row[20],
            conference=first_row[21],
            division=first_row[22],
        )
        if first_row[10]
        else None
    )

    away_team = (
        Team(
            team_id=first_row[23],
            full_name=first_row[24],
            abbreviation=first_row[25],
            nickname=first_row[26],
            city=first_row[27],
            state=first_row[28],
            year_founded=first_row[29],
            arena=first_row[30],
            owner=first_row[31],
            general_manager=first_row[32],
            head_coach=first_row[33],
            conference=first_row[34],
            division=first_row[35],
        )
        if first_row[23]
        else None
    )

    # Extract player stats
    home_players: list[PlayerGameStats] = []
    away_players: list[PlayerGameStats] = []

    for row in rows:
        # Skip rows with no player stats (pgs.stat_id is NULL)
        if row[36] is None:
            continue
        stats = PlayerGameStats(
            stat_id=row[36],
            game_id=game_id,
            player_id=row[37],
            team_id=row[38],
            minutes_played=row[39],
            points=row[40] or 0,
            rebounds_offensive=row[41] or 0,
            rebounds_defensive=row[42] or 0,
            assists=row[43] or 0,
            steals=row[44] or 0,
            blocks=row[45] or 0,
            turnovers=row[46] or 0,
            personal_fouls=row[47] or 0,
            fg_made=row[48] or 0,
            fg_attempted=row[49] or 0,
            fg3_made=row[50] or 0,
            fg3_attempted=row[51] or 0,
            ft_made=row[52] or 0,
            ft_attempted=row[53] or 0,
        )
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


@router.get("/{game_id}/export")
async def export_game_data(
    game_id: str,
    format: Annotated[str, Query(description="Export format (csv or json)")] = "csv",
) -> Response:
    """Export game box score to CSV or JSON.

    Path Parameters:
        - game_id: Unique identifier for the game

    Query Parameters:
        - format: Export format ('csv' or 'json')

    Returns:
        CSV or JSON file download response.
    """
    format_type = format.lower()
    if format_type not in ["csv", "json"]:
        format_type = "csv"

    return export_box_score(game_id, format_type)
