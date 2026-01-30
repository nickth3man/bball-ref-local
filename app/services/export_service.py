"""Export service for CSV and JSON data export functionality.

Provides utilities to export player stats, team stats, and game logs
in CSV and JSON formats.
"""

import csv
import io
import json
from datetime import date, datetime
from typing import Any, Protocol

from fastapi import HTTPException
from fastapi.responses import Response

from app.services.database import execute_query


class ExportableData(Protocol):
    """Protocol for data that can be exported."""

    def model_dump(self) -> dict[str, Any]: ...


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle decimal and date types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def _format_value(value: Any) -> str:
    """Format a value for CSV output.

    Args:
        value: The value to format.

    Returns:
        Formatted string representation.
    """
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _build_csv_response(data: list[dict[str, Any]], filename: str) -> Response:
    """Build a CSV response from data.

    Args:
        data: List of dictionaries to export.
        filename: Name of the file to download.

    Returns:
        FastAPI Response with CSV content with UTF-8 BOM for Excel compatibility.
    """
    if not data:
        raise HTTPException(status_code=404, detail="No data to export")

    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    headers = list(data[0].keys())
    writer.writerow(headers)

    # Write data rows
    for row in data:
        formatted_row = [_format_value(row.get(key)) for key in headers]
        writer.writerow(formatted_row)

    output.seek(0)

    # Add UTF-8 BOM for Excel compatibility
    csv_content = output.getvalue()
    csv_bytes = csv_content.encode("utf-8-sig")  # utf-8-sig adds BOM

    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )


def _build_json_response(data: list[dict[str, Any]], filename: str) -> Response:
    """Build a JSON response from data.

    Args:
        data: List of dictionaries to export.
        filename: Name of the file to download.

    Returns:
        FastAPI Response with JSON content.
    """
    if not data:
        raise HTTPException(status_code=404, detail="No data to export")

    json_content = json.dumps(data, cls=DecimalEncoder, indent=2)

    return Response(
        content=json_content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}.json"},
    )


def export_to_csv(data: list[dict[str, Any]], filename: str) -> Response:
    """Generic CSV export function.

    Args:
        data: List of dictionaries to export.
        filename: Name of the file to download (without extension).

    Returns:
        FastAPI Response with CSV content.
    """
    return _build_csv_response(data, filename)


def export_to_json(data: list[dict[str, Any]], filename: str) -> Response:
    """Generic JSON export function.

    Args:
        data: List of dictionaries to export.
        filename: Name of the file to download (without extension).

    Returns:
        FastAPI Response with JSON content.
    """
    return _build_json_response(data, filename)


def export_player_stats(player_id: str, format_type: str = "csv") -> Response:
    """Export player statistics to CSV or JSON.

    Args:
        player_id: The player's unique identifier.
        format_type: Export format ('csv' or 'json').

    Returns:
        FastAPI Response with exported data.
    """
    query = """
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
            CASE WHEN SUM(fg_attempted) > 0
                THEN ROUND(SUM(fg_made)::FLOAT / SUM(fg_attempted), 3)
                ELSE NULL
            END as fg_pct,
            SUM(fg3_made) as fg3_made,
            SUM(fg3_attempted) as fg3_attempted,
            CASE WHEN SUM(fg3_attempted) > 0
                THEN ROUND(SUM(fg3_made)::FLOAT / SUM(fg3_attempted), 3)
                ELSE NULL
            END as fg3_pct,
            SUM(ft_made) as ft_made,
            SUM(ft_attempted) as ft_attempted,
            CASE WHEN SUM(ft_attempted) > 0
                THEN ROUND(SUM(ft_made)::FLOAT / SUM(ft_attempted), 3)
                ELSE NULL
            END as ft_pct,
            SUM(turnovers) as turnovers,
            SUM(personal_fouls) as personal_fouls
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        WHERE pgs.player_id = ?
        GROUP BY g.season
        ORDER BY g.season DESC
    """

    try:
        rows = execute_query(query, [player_id])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch player stats: {e}") from e

    columns = [
        "season", "games_played", "minutes", "points", "rebounds",
        "assists", "steals", "blocks", "fg_made", "fg_attempted", "fg_pct",
        "fg3_made", "fg3_attempted", "fg3_pct", "ft_made", "ft_attempted", "ft_pct",
        "turnovers", "personal_fouls",
    ]

    data = [dict(zip(columns, row, strict=True)) for row in rows]

    filename = f"player_{player_id}_stats"

    if format_type.lower() == "json":
        return _build_json_response(data, filename)
    return _build_csv_response(data, filename)


def export_team_stats(team_id: str, format_type: str = "csv") -> Response:
    """Export team statistics to CSV or JSON.

    Args:
        team_id: The team's unique identifier.
        format_type: Export format ('csv' or 'json').

    Returns:
        FastAPI Response with exported data.
    """
    query = """
        SELECT
            g.season,
            COUNT(DISTINCT g.game_id) as games_played,
            SUM(CASE WHEN g.winner_team_id = ? THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN g.winner_team_id != ? AND g.winner_team_id IS NOT NULL THEN 1 ELSE 0 END) as losses,
            SUM(pgs.points) as points_for,
            AVG(pgs.points) as avg_points,
            SUM(pgs.fg_made) as fg_made,
            SUM(pgs.fg_attempted) as fg_attempted,
            CASE WHEN SUM(pgs.fg_attempted) > 0
                THEN ROUND(SUM(pgs.fg_made)::FLOAT / SUM(pgs.fg_attempted), 3)
                ELSE NULL
            END as fg_pct,
            SUM(pgs.fg3_made) as fg3_made,
            SUM(pgs.fg3_attempted) as fg3_attempted,
            CASE WHEN SUM(pgs.fg3_attempted) > 0
                THEN ROUND(SUM(pgs.fg3_made)::FLOAT / SUM(pgs.fg3_attempted), 3)
                ELSE NULL
            END as fg3_pct,
            SUM(pgs.ft_made) as ft_made,
            SUM(pgs.ft_attempted) as ft_attempted,
            SUM(pgs.rebounds_offensive + pgs.rebounds_defensive) as rebounds,
            SUM(pgs.assists) as assists,
            SUM(pgs.steals) as steals,
            SUM(pgs.blocks) as blocks,
            SUM(pgs.turnovers) as turnovers
        FROM games g
        LEFT JOIN player_game_stats pgs ON g.game_id = pgs.game_id AND pgs.team_id = ?
        WHERE (g.home_team_id = ? OR g.away_team_id = ?)
        AND g.status = 'final'
        GROUP BY g.season
        ORDER BY g.season DESC
    """

    try:
        rows = execute_query(query, [team_id, team_id, team_id, team_id, team_id])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch team stats: {e}") from e

    columns = [
        "season", "games_played", "wins", "losses", "points_for", "avg_points",
        "fg_made", "fg_attempted", "fg_pct", "fg3_made", "fg3_attempted", "fg3_pct",
        "ft_made", "ft_attempted", "rebounds", "assists", "steals", "blocks", "turnovers",
    ]

    data = [dict(zip(columns, row, strict=True)) for row in rows]

    filename = f"team_{team_id}_stats"

    if format_type.lower() == "json":
        return _build_json_response(data, filename)
    return _build_csv_response(data, filename)


def export_game_logs(
    player_id: str,
    season: int | None = None,
    format_type: str = "csv",
) -> Response:
    """Export player game logs to CSV or JSON.

    Args:
        player_id: The player's unique identifier.
        season: Optional season filter.
        format_type: Export format ('csv' or 'json').

    Returns:
        FastAPI Response with exported data.
    """
    season_filter = "AND g.season = ?" if season else ""
    params: list[Any] = [player_id]
    if season:
        params.append(season)

    query = f"""
        SELECT
            g.game_date,
            g.season,
            ht.abbreviation as opponent,
            CASE WHEN pgs.team_id = g.home_team_id THEN 'Home' ELSE 'Away' END as home_away,
            CASE
                WHEN (pgs.team_id = g.home_team_id AND g.home_score > g.away_score)
                     OR (pgs.team_id = g.away_team_id AND g.away_score > g.home_score)
                THEN 'Win'
                ELSE 'Loss'
            END as result,
            CASE
                WHEN pgs.team_id = g.home_team_id THEN g.home_score
                ELSE g.away_score
            END as team_score,
            CASE
                WHEN pgs.team_id = g.home_team_id THEN g.away_score
                ELSE g.home_score
            END as opponent_score,
            pgs.minutes_played,
            pgs.points,
            pgs.rebounds_offensive + pgs.rebounds_defensive as rebounds,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.fg_made,
            pgs.fg_attempted,
            CASE WHEN pgs.fg_attempted > 0
                THEN ROUND(pgs.fg_made::FLOAT / pgs.fg_attempted, 3)
                ELSE NULL
            END as fg_pct,
            pgs.fg3_made,
            pgs.fg3_attempted,
            CASE WHEN pgs.fg3_attempted > 0
                THEN ROUND(pgs.fg3_made::FLOAT / pgs.fg3_attempted, 3)
                ELSE NULL
            END as fg3_pct,
            pgs.ft_made,
            pgs.ft_attempted,
            CASE WHEN pgs.ft_attempted > 0
                THEN ROUND(pgs.ft_made::FLOAT / pgs.ft_attempted, 3)
                ELSE NULL
            END as ft_pct,
            pgs.turnovers,
            pgs.personal_fouls
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        LEFT JOIN teams ht ON CASE
            WHEN pgs.team_id = g.home_team_id THEN g.away_team_id
            ELSE g.home_team_id
        END = ht.team_id
        WHERE pgs.player_id = ? {season_filter}
        ORDER BY g.game_date DESC
    """

    try:
        rows = execute_query(query, params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch game logs: {e}") from e

    columns = [
        "game_date", "season", "opponent", "home_away", "result",
        "team_score", "opponent_score", "minutes_played", "points", "rebounds",
        "assists", "steals", "blocks", "fg_made", "fg_attempted", "fg_pct",
        "fg3_made", "fg3_attempted", "fg3_pct", "ft_made", "ft_attempted", "ft_pct",
        "turnovers", "personal_fouls",
    ]

    data = [dict(zip(columns, row, strict=True)) for row in rows]

    filename = f"player_{player_id}_gamelog{'_' + str(season) if season else ''}"

    if format_type.lower() == "json":
        return _build_json_response(data, filename)
    return _build_csv_response(data, filename)


def export_box_score(game_id: str, format_type: str = "csv") -> Response:
    """Export game box score to CSV or JSON.

    Args:
        game_id: The game's unique identifier.
        format_type: Export format ('csv' or 'json').

    Returns:
        FastAPI Response with exported data.
    """
    query = """
        SELECT
            p.first_name || ' ' || p.last_name as player_name,
            t.abbreviation as team,
            pgs.minutes_played,
            pgs.points,
            pgs.rebounds_offensive + pgs.rebounds_defensive as rebounds,
            pgs.assists,
            pgs.steals,
            pgs.blocks,
            pgs.fg_made,
            pgs.fg_attempted,
            CASE WHEN pgs.fg_attempted > 0
                THEN ROUND(pgs.fg_made::FLOAT / pgs.fg_attempted, 3)
                ELSE NULL
            END as fg_pct,
            pgs.fg3_made,
            pgs.fg3_attempted,
            CASE WHEN pgs.fg3_attempted > 0
                THEN ROUND(pgs.fg3_made::FLOAT / pgs.fg3_attempted, 3)
                ELSE NULL
            END as fg3_pct,
            pgs.ft_made,
            pgs.ft_attempted,
            CASE WHEN pgs.ft_attempted > 0
                THEN ROUND(pgs.ft_made::FLOAT / pgs.ft_attempted, 3)
                ELSE NULL
            END as ft_pct,
            pgs.turnovers,
            pgs.personal_fouls
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.player_id
        JOIN teams t ON pgs.team_id = t.team_id
        WHERE pgs.game_id = ?
        ORDER BY t.team_id, pgs.points DESC
    """

    try:
        rows = execute_query(query, [game_id])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch box score: {e}") from e

    columns = [
        "player_name", "team", "minutes_played", "points", "rebounds",
        "assists", "steals", "blocks", "fg_made", "fg_attempted", "fg_pct",
        "fg3_made", "fg3_attempted", "fg3_pct", "ft_made", "ft_attempted", "ft_pct",
        "turnovers", "personal_fouls",
    ]

    data = [dict(zip(columns, row, strict=True)) for row in rows]

    filename = f"game_{game_id}_boxscore"

    if format_type.lower() == "json":
        return _build_json_response(data, filename)
    return _build_csv_response(data, filename)
