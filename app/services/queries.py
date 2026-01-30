"""Database query service for basketball statistics.

This module provides entity-specific query functions for retrieving
data from the DuckDB database. All functions use parameterized queries
for security and return dictionaries mapping to Pydantic model fields.
"""

from typing import Any

from app.services.database import execute_query

# ============================================================================
# Player Queries
# ============================================================================


def get_players(
    search: str | None = None,
    team_id: int | None = None,
    position: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Get players with optional filtering and pagination.

    Args:
        search: Search string for first or last name (case-insensitive).
        team_id: Filter by team ID.
        position: Filter by position (PG, SG, SF, PF, C).
        page: Page number (1-indexed).
        page_size: Number of results per page.

    Returns:
        Tuple of (list of player dicts, total count).
    """
    params: list[Any] = []
    where_clauses = []

    if search:
        where_clauses.append("(LOWER(first_name) LIKE LOWER(?) OR LOWER(last_name) LIKE LOWER(?))")
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
    count_result = execute_query(count_query, params)
    total_count = count_result[0][0] if count_result else 0

    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
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
        WHERE {where_sql}
        ORDER BY last_name, first_name
        LIMIT ? OFFSET ?
    """
    params.extend([page_size, offset])

    results = execute_query(query, params)

    players = [
        {
            "player_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "team_id": row[3],
            "position": row[4],
            "jersey_number": row[5],
            "height": row[6],
            "weight": row[7],
            "birth_date": row[8],
            "country": row[9],
            "draft_year": row[10],
            "draft_round": row[11],
            "draft_number": row[12],
        }
        for row in results
    ]

    return players, total_count


def get_player_by_id(player_id: int) -> dict | None:
    """Get a single player by ID.

    Args:
        player_id: The player's unique ID.

    Returns:
        Player dict or None if not found.
    """
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
        WHERE player_id = ?
    """
    results = execute_query(query, [player_id])

    if not results:
        return None

    row = results[0]
    return {
        "player_id": row[0],
        "first_name": row[1],
        "last_name": row[2],
        "team_id": row[3],
        "position": row[4],
        "jersey_number": row[5],
        "height": row[6],
        "weight": row[7],
        "birth_date": row[8],
        "country": row[9],
        "draft_year": row[10],
        "draft_round": row[11],
        "draft_number": row[12],
    }


def get_player_season_stats(player_id: int, season: int | None = None) -> dict:
    """Get aggregated season stats for a player.

    Args:
        player_id: The player's unique ID.
        season: Optional season year filter.

    Returns:
        Dictionary with aggregated season statistics.
    """
    params: list[Any] = [player_id]
    season_filter = "AND g.season = ?" if season else ""
    if season:
        params.append(season)

    query = f"""
        SELECT
            COUNT(DISTINCT g.game_id) as games_played,
            SUM(pgs.minutes_played) as total_minutes,
            SUM(pgs.points) as total_points,
            SUM(pgs.rebounds_offensive) as total_offensive_rebounds,
            SUM(pgs.rebounds_defensive) as total_defensive_rebounds,
            SUM(pgs.assists) as total_assists,
            SUM(pgs.steals) as total_steals,
            SUM(pgs.blocks) as total_blocks,
            SUM(pgs.turnovers) as total_turnovers,
            SUM(pgs.personal_fouls) as total_fouls,
            SUM(pgs.fg_made) as total_fg_made,
            SUM(pgs.fg_attempted) as total_fg_attempted,
            SUM(pgs.fg3_made) as total_fg3_made,
            SUM(pgs.fg3_attempted) as total_fg3_attempted,
            SUM(pgs.ft_made) as total_ft_made,
            SUM(pgs.ft_attempted) as total_ft_attempted,
            AVG(pgs.points) as avg_points,
            AVG(pgs.assists) as avg_assists,
            AVG(pgs.rebounds_offensive + pgs.rebounds_defensive) as avg_rebounds,
            MIN(g.season) as season_from,
            MAX(g.season) as season_to
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ? {season_filter}
    """

    results = execute_query(query, params)

    if not results or results[0][0] == 0:
        return {
            "player_id": player_id,
            "season": season,
            "games_played": 0,
            "total_minutes": 0.0,
            "total_points": 0,
            "total_rebounds": 0,
            "total_assists": 0,
            "total_steals": 0,
            "total_blocks": 0,
            "total_turnovers": 0,
            "total_fouls": 0,
            "avg_points": 0.0,
            "avg_assists": 0.0,
            "avg_rebounds": 0.0,
            "fg_pct": None,
            "fg3_pct": None,
            "ft_pct": None,
        }

    row = results[0]
    games_played = row[0]
    fg_made = row[10] or 0
    fg_attempted = row[11] or 0
    fg3_made = row[12] or 0
    fg3_attempted = row[13] or 0
    ft_made = row[14] or 0
    ft_attempted = row[15] or 0

    return {
        "player_id": player_id,
        "season": season,
        "games_played": games_played,
        "total_minutes": row[1] or 0.0,
        "total_points": row[2] or 0,
        "total_offensive_rebounds": row[3] or 0,
        "total_defensive_rebounds": row[4] or 0,
        "total_rebounds": (row[3] or 0) + (row[4] or 0),
        "total_assists": row[5] or 0,
        "total_steals": row[6] or 0,
        "total_blocks": row[7] or 0,
        "total_turnovers": row[8] or 0,
        "total_fouls": row[9] or 0,
        "total_fg_made": fg_made,
        "total_fg_attempted": fg_attempted,
        "total_fg3_made": fg3_made,
        "total_fg3_attempted": fg3_attempted,
        "total_ft_made": ft_made,
        "total_ft_attempted": ft_attempted,
        "avg_points": row[16] or 0.0,
        "avg_assists": row[17] or 0.0,
        "avg_rebounds": row[18] or 0.0,
        "fg_pct": round(fg_made / fg_attempted, 3) if fg_attempted > 0 else None,
        "fg3_pct": round(fg3_made / fg3_attempted, 3) if fg3_attempted > 0 else None,
        "ft_pct": round(ft_made / ft_attempted, 3) if ft_attempted > 0 else None,
        "season_from": row[19],
        "season_to": row[20],
    }


def get_player_game_logs(player_id: int, season: int | None = None, limit: int = 100) -> list[dict]:
    """Get game logs for a player.

    Args:
        player_id: The player's unique ID.
        season: Optional season year filter.
        limit: Maximum number of games to return.

    Returns:
        List of game log dictionaries.
    """
    params: list[Any] = [player_id]
    season_filter = "AND g.season = ?" if season else ""
    if season:
        params.append(season)
    params.append(limit)

    query = f"""
        SELECT
            g.game_id,
            g.game_date,
            g.season,
            g.season_type,
            g.home_team_id,
            g.away_team_id,
            g.home_score,
            g.away_score,
            g.status,
            pgs.team_id as player_team_id,
            pgs.minutes_played,
            pgs.points,
            pgs.rebounds_offensive,
            pgs.rebounds_defensive,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.turnovers,
            pgs.personal_fouls,
            pgs.fg_made,
            pgs.fg_attempted,
            pgs.fg3_made,
            pgs.fg3_attempted,
            pgs.ft_made,
            pgs.ft_attempted
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ? {season_filter}
        ORDER BY g.game_date DESC
        LIMIT ?
    """

    results = execute_query(query, params)

    return [
        {
            "game_id": row[0],
            "game_date": row[1],
            "season": row[2],
            "season_type": row[3],
            "home_team_id": row[4],
            "away_team_id": row[5],
            "home_score": row[6],
            "away_score": row[7],
            "status": row[8],
            "player_team_id": row[9],
            "minutes_played": row[10],
            "points": row[11],
            "rebounds_offensive": row[12],
            "rebounds_defensive": row[13],
            "assists": row[14],
            "steals": row[15],
            "blocks": row[16],
            "turnovers": row[17],
            "personal_fouls": row[18],
            "fg_made": row[19],
            "fg_attempted": row[20],
            "fg3_made": row[21],
            "fg3_attempted": row[22],
            "ft_made": row[23],
            "ft_attempted": row[24],
        }
        for row in results
    ]


# ============================================================================
# Team Queries
# ============================================================================


def get_teams(conference: str | None = None, division: str | None = None) -> list[dict]:
    """Get teams with optional filtering.

    Args:
        conference: Filter by conference (Eastern or Western).
        division: Filter by division.

    Returns:
        List of team dictionaries.
    """
    params: list[Any] = []
    where_clauses = []

    if conference:
        where_clauses.append("conference = ?")
        params.append(conference)

    if division:
        where_clauses.append("division = ?")
        params.append(division)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
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
        WHERE {where_sql}
        ORDER BY full_name
    """

    results = execute_query(query, params)

    return [
        {
            "team_id": row[0],
            "full_name": row[1],
            "abbreviation": row[2],
            "nickname": row[3],
            "city": row[4],
            "state": row[5],
            "year_founded": row[6],
            "arena": row[7],
            "owner": row[8],
            "general_manager": row[9],
            "head_coach": row[10],
            "conference": row[11],
            "division": row[12],
        }
        for row in results
    ]


def get_team_by_id(team_id: int) -> dict | None:
    """Get a single team by ID.

    Args:
        team_id: The team's unique ID.

    Returns:
        Team dict or None if not found.
    """
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
    results = execute_query(query, [team_id])

    if not results:
        return None

    row = results[0]
    return {
        "team_id": row[0],
        "full_name": row[1],
        "abbreviation": row[2],
        "nickname": row[3],
        "city": row[4],
        "state": row[5],
        "year_founded": row[6],
        "arena": row[7],
        "owner": row[8],
        "general_manager": row[9],
        "head_coach": row[10],
        "conference": row[11],
        "division": row[12],
    }


def get_team_roster(team_id: int) -> list[dict]:
    """Get current roster for a team.

    Args:
        team_id: The team's unique ID.

    Returns:
        List of player dictionaries.
    """
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
        ORDER BY position, last_name, first_name
    """

    results = execute_query(query, [team_id])

    return [
        {
            "player_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "team_id": row[3],
            "position": row[4],
            "jersey_number": row[5],
            "height": row[6],
            "weight": row[7],
            "birth_date": row[8],
            "country": row[9],
            "draft_year": row[10],
            "draft_round": row[11],
            "draft_number": row[12],
        }
        for row in results
    ]


def get_team_season_stats(team_id: int, season: int) -> dict | None:
    """Get season statistics for a team.

    Args:
        team_id: The team's unique ID.
        season: The season year.

    Returns:
        Dictionary with team season statistics or None if no data.
    """
    # Get game results for wins/losses
    games_query = """
        SELECT
            COUNT(*) as total_games,
            SUM(CASE WHEN winner_team_id = ? THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN winner_team_id IS NOT NULL AND winner_team_id != ? THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN home_team_id = ? THEN home_score ELSE away_score END) as points_for,
            SUM(CASE WHEN home_team_id = ? THEN away_score ELSE home_score END) as points_against,
            AVG(CASE WHEN home_team_id = ? THEN home_score ELSE away_score END) as avg_points_for,
            AVG(CASE WHEN home_team_id = ? THEN away_score ELSE home_score END) as avg_points_against
        FROM games
        WHERE (home_team_id = ? OR away_team_id = ?)
            AND season = ?
            AND status = 'final'
    """
    games_params = [team_id] * 7 + [team_id, team_id, season]
    games_results = execute_query(games_query, games_params)

    if not games_results or games_results[0][0] == 0:
        return None

    row = games_results[0]
    total_games = row[0]
    wins = row[1] or 0
    losses = row[2] or 0
    points_for = row[3] or 0
    points_against = row[4] or 0

    # Get aggregated player stats for the team
    stats_query = """
        SELECT
            SUM(points) as total_points,
            SUM(rebounds_offensive + rebounds_defensive) as total_rebounds,
            SUM(assists) as total_assists,
            SUM(steals) as total_steals,
            SUM(blocks) as total_blocks,
            SUM(turnovers) as total_turnovers,
            SUM(fg_made) as total_fg_made,
            SUM(fg_attempted) as total_fg_attempted,
            SUM(fg3_made) as total_fg3_made,
            SUM(fg3_attempted) as total_fg3_attempted,
            SUM(ft_made) as total_ft_made,
            SUM(ft_attempted) as total_ft_attempted
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.team_id = ? AND g.season = ?
    """
    stats_results = execute_query(stats_query, [team_id, season])

    stats_row = stats_results[0] if stats_results else [0] * 11
    fg_made = stats_row[6] or 0
    fg_attempted = stats_row[7] or 0
    fg3_made = stats_row[8] or 0
    fg3_attempted = stats_row[9] or 0
    ft_made = stats_row[10] or 0
    ft_attempted = stats_row[11] or 0 if len(stats_row) > 11 else 0

    return {
        "team_id": team_id,
        "season": season,
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "win_pct": round(wins / total_games, 3) if total_games > 0 else 0.0,
        "points_for": points_for,
        "points_against": points_against,
        "point_differential": points_for - points_against,
        "avg_points_for": row[5] or 0.0,
        "avg_points_against": row[6] or 0.0,
        "total_points": stats_row[0] or 0,
        "total_rebounds": stats_row[1] or 0,
        "total_assists": stats_row[2] or 0,
        "total_steals": stats_row[3] or 0,
        "total_blocks": stats_row[4] or 0,
        "total_turnovers": stats_row[5] or 0,
        "fg_pct": round(fg_made / fg_attempted, 3) if fg_attempted > 0 else None,
        "fg3_pct": round(fg3_made / fg3_attempted, 3) if fg3_attempted > 0 else None,
        "ft_pct": round(ft_made / ft_attempted, 3) if ft_attempted > 0 else None,
    }


# ============================================================================
# Game Queries
# ============================================================================


def get_games(
    date_from: str | None = None,
    date_to: str | None = None,
    team_id: int | None = None,
    season: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Get games with optional filtering and pagination.

    Args:
        date_from: Start date filter (YYYY-MM-DD).
        date_to: End date filter (YYYY-MM-DD).
        team_id: Filter by team ID (home or away).
        season: Filter by season year.
        page: Page number (1-indexed).
        page_size: Number of results per page.

    Returns:
        Tuple of (list of game dicts, total count).
    """
    params: list[Any] = []
    where_clauses = []

    if date_from:
        where_clauses.append("game_date >= ?")
        params.append(date_from)

    if date_to:
        where_clauses.append("game_date <= ?")
        params.append(date_to)

    if team_id is not None:
        where_clauses.append("(home_team_id = ? OR away_team_id = ?)")
        params.extend([team_id, team_id])

    if season:
        where_clauses.append("season = ?")
        params.append(season)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Get total count
    count_query = f"SELECT COUNT(*) FROM games WHERE {where_sql}"
    count_result = execute_query(count_query, params.copy())
    total_count = count_result[0][0] if count_result else 0

    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
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
        WHERE {where_sql}
        ORDER BY game_date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([page_size, offset])

    results = execute_query(query, params)

    games = [
        {
            "game_id": row[0],
            "season": row[1],
            "season_type": row[2],
            "game_date": row[3],
            "home_team_id": row[4],
            "away_team_id": row[5],
            "home_score": row[6],
            "away_score": row[7],
            "winner_team_id": row[8],
            "status": row[9],
        }
        for row in results
    ]

    return games, total_count


def get_game_by_id(game_id: str) -> dict | None:
    """Get a single game by ID.

    Args:
        game_id: The game's unique ID.

    Returns:
        Game dict or None if not found.
    """
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
        WHERE game_id = ?
    """
    results = execute_query(query, [game_id])

    if not results:
        return None

    row = results[0]
    return {
        "game_id": row[0],
        "season": row[1],
        "season_type": row[2],
        "game_date": row[3],
        "home_team_id": row[4],
        "away_team_id": row[5],
        "home_score": row[6],
        "away_score": row[7],
        "winner_team_id": row[8],
        "status": row[9],
    }


def get_game_box_score(game_id: str) -> dict:
    """Get game details with player statistics.

    Args:
        game_id: The game's unique ID.

    Returns:
        Dictionary with game info and player stats.
    """
    # Get game info
    game = get_game_by_id(game_id)
    if not game:
        return {"game": None, "home_team_stats": [], "away_team_stats": []}

    # Get player stats with player info
    query = """
        SELECT
            pgs.player_id,
            p.first_name,
            p.last_name,
            pgs.team_id,
            p.position,
            p.jersey_number,
            pgs.minutes_played,
            pgs.points,
            pgs.rebounds_offensive,
            pgs.rebounds_defensive,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.turnovers,
            pgs.personal_fouls,
            pgs.fg_made,
            pgs.fg_attempted,
            pgs.fg3_made,
            pgs.fg3_attempted,
            pgs.ft_made,
            pgs.ft_attempted
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.player_id
        WHERE pgs.game_id = ?
        ORDER BY pgs.team_id, pgs.points DESC, p.last_name
    """

    results = execute_query(query, [game_id])

    home_team_stats = []
    away_team_stats = []

    for row in results:
        stat = {
            "player_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "team_id": row[3],
            "position": row[4],
            "jersey_number": row[5],
            "minutes_played": row[6],
            "points": row[7],
            "rebounds_offensive": row[8],
            "rebounds_defensive": row[9],
            "assists": row[10],
            "steals": row[11],
            "blocks": row[12],
            "turnovers": row[13],
            "personal_fouls": row[14],
            "fg_made": row[15],
            "fg_attempted": row[16],
            "fg3_made": row[17],
            "fg3_attempted": row[18],
            "ft_made": row[19],
            "ft_attempted": row[20],
        }

        if row[3] == game["home_team_id"]:
            home_team_stats.append(stat)
        else:
            away_team_stats.append(stat)

    return {
        "game": game,
        "home_team_stats": home_team_stats,
        "away_team_stats": away_team_stats,
    }


def get_todays_games() -> list[dict]:
    """Get games scheduled for today.

    Returns:
        List of game dictionaries for today's date.
    """
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
        WHERE game_date = CURRENT_DATE
        ORDER BY game_id
    """

    results = execute_query(query)

    return [
        {
            "game_id": row[0],
            "season": row[1],
            "season_type": row[2],
            "game_date": row[3],
            "home_team_id": row[4],
            "away_team_id": row[5],
            "home_score": row[6],
            "away_score": row[7],
            "winner_team_id": row[8],
            "status": row[9],
        }
        for row in results
    ]


# ============================================================================
# Stats Queries
# ============================================================================


def get_league_leaders(category: str, season: int, limit: int = 10) -> list[dict]:
    """Get league leaders for a statistical category.

    Args:
        category: Statistical category (points, assists, rebounds, steals, blocks).
        season: The season year.
        limit: Number of leaders to return.

    Returns:
        List of player dictionaries with stat totals.
    """
    valid_categories = {
        "points": "points",
        "assists": "assists",
        "rebounds": "rebounds_offensive + rebounds_defensive",
        "steals": "steals",
        "blocks": "blocks",
    }

    if category.lower() not in valid_categories:
        return []

    stat_column = valid_categories[category.lower()]

    query = f"""
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            t.abbreviation as team_abbreviation,
            p.position,
            COUNT(pgs.game_id) as games_played,
            SUM(pgs.{stat_column}) as total_stat,
            AVG(pgs.{stat_column}) as avg_stat
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        JOIN players p ON pgs.player_id = p.player_id
        JOIN teams t ON p.team_id = t.team_id
        WHERE g.season = ?
        GROUP BY p.player_id, p.first_name, p.last_name, t.abbreviation, p.position
        HAVING COUNT(pgs.game_id) >= 10
        ORDER BY total_stat DESC
        LIMIT ?
    """

    results = execute_query(query, [season, limit])

    return [
        {
            "player_id": row[0],
            "first_name": row[1],
            "last_name": row[2],
            "team_abbreviation": row[3],
            "position": row[4],
            "games_played": row[5],
            "total": row[6],
            "average": round(row[7], 1) if row[7] else 0.0,
            "category": category.lower(),
        }
        for row in results
    ]


def get_standings(season: int, conference: str | None = None) -> list[dict]:
    """Get league standings for a season.

    Args:
        season: The season year.
        conference: Optional conference filter (Eastern or Western).

    Returns:
        List of team standing dictionaries.
    """
    params: list[Any] = [season]
    conference_filter = "AND t.conference = ?" if conference else ""
    if conference:
        params.append(conference)

    query = f"""
        SELECT
            t.team_id,
            t.full_name,
            t.abbreviation,
            t.conference,
            t.division,
            COUNT(CASE WHEN g.status = 'final' THEN 1 END) as games_played,
            SUM(CASE WHEN g.winner_team_id = t.team_id THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN g.winner_team_id IS NOT NULL AND g.winner_team_id != t.team_id THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN g.home_team_id = t.team_id THEN g.home_score ELSE g.away_score END) as points_for,
            SUM(CASE WHEN g.home_team_id = t.team_id THEN g.away_score ELSE g.home_score END) as points_against
        FROM teams t
        LEFT JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
            AND g.season = ?
            AND g.season_type = 'Regular Season'
        WHERE 1=1 {conference_filter}
        GROUP BY t.team_id, t.full_name, t.abbreviation, t.conference, t.division
        HAVING games_played > 0
        ORDER BY t.conference, t.division, wins DESC, (points_for - points_against) DESC
    """

    results = execute_query(query, params)

    standings = []
    for row in results:
        wins = row[6] or 0
        losses = row[7] or 0
        games = row[5] or 0
        standings.append(
            {
                "team_id": row[0],
                "full_name": row[1],
                "abbreviation": row[2],
                "conference": row[3],
                "division": row[4],
                "games_played": games,
                "wins": wins,
                "losses": losses,
                "win_pct": round(wins / games, 3) if games > 0 else 0.0,
                "points_for": row[8] or 0,
                "points_against": row[9] or 0,
                "point_differential": (row[8] or 0) - (row[9] or 0),
            }
        )

    return standings
