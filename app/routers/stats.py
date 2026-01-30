"""Stats API router for league leaders and standings.

Provides endpoints for retrieving league statistical leaders and team standings
for a given season.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.models.player import Player
from app.models.team import Team
from app.services.database import execute_query
from app.services.htmx_utils import get_templates, is_htmx_request

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])

# Valid statistical categories for leaders
VALID_CATEGORIES = {
    "points",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "fg_pct",
    "fg3_pct",
    "ft_pct",
}

# Mapping of category names to database column names
CATEGORY_COLUMN_MAP = {
    "points": "points",
    "rebounds": "rebounds_total",
    "assists": "assists",
    "steals": "steals",
    "blocks": "blocks",
    "fg_pct": "fg_pct",
    "fg3_pct": "fg3_pct",
    "ft_pct": "ft_pct",
}


class LeaderEntry(BaseModel):
    """Single leader entry in the league leaders list.

    Attributes:
        rank: Ranking position (1 = leader).
        player: Player information.
        team: Team information.
        value: Statistical value for the category.
        games: Number of games played.
    """

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(description="Ranking position (1 = leader)", ge=1)
    player: Player = Field(description="Player information")
    team: Team = Field(description="Team information")
    value: float = Field(description="Statistical value for the category")
    games: int = Field(description="Number of games played", ge=0)


class LeadersResponse(BaseModel):
    """Response model for league leaders endpoint.

    Attributes:
        category: Statistical category (points, rebounds, etc.).
        season: Season year.
        leaders: List of leader entries ordered by rank.
    """

    model_config = ConfigDict(from_attributes=True)

    category: str = Field(description="Statistical category")
    season: int = Field(description="Season year", ge=1946)
    leaders: list[LeaderEntry] = Field(description="List of leader entries ordered by rank")


class StandingsEntry(BaseModel):
    """Single team entry in the standings.

    Attributes:
        team: Team information.
        wins: Number of wins.
        losses: Number of losses.
        win_pct: Win percentage (0.0 to 1.0).
        home_record: Home record as string (e.g., "25-10").
        away_record: Away record as string (e.g., "15-20").
        division: Division name.
        conference_rank: Rank within conference.
        division_rank: Rank within division.
    """

    model_config = ConfigDict(from_attributes=True)

    team: Team = Field(description="Team information")
    wins: int = Field(description="Number of wins", ge=0)
    losses: int = Field(description="Number of losses", ge=0)
    win_pct: float = Field(description="Win percentage", ge=0.0, le=1.0)
    home_record: str = Field(description="Home record (e.g., '25-10')")
    away_record: str = Field(description="Away record (e.g., '15-20')")
    division: str = Field(description="Division name")
    conference_rank: int = Field(description="Rank within conference", ge=1)
    division_rank: int = Field(description="Rank within division", ge=1)


class StandingsResponse(BaseModel):
    """Response model for team standings endpoint.

    Attributes:
        season: Season year.
        conference: Conference filter if applied (Eastern or Western).
        standings: List of team standings ordered by conference rank.
    """

    model_config = ConfigDict(from_attributes=True)

    season: int = Field(description="Season year", ge=1946)
    conference: str | None = Field(default=None, description="Conference filter if applied")
    standings: list[StandingsEntry] = Field(description="List of team standings ordered by rank")


def _validate_category(category: str) -> None:
    """Validate the statistical category.

    Args:
        category: The category to validate.

    Raises:
        HTTPException: If category is invalid.
    """
    if category not in VALID_CATEGORIES:
        valid_list = ", ".join(sorted(VALID_CATEGORIES))
        raise HTTPException(
            status_code=400, detail=f"Invalid category '{category}'. Valid categories: {valid_list}"
        )


def _build_leaders_query(category: str) -> str:
    """Build the SQL query for league leaders.

    Args:
        category: The statistical category.

    Returns:
        The SQL query string.
    """
    stat_column = CATEGORY_COLUMN_MAP[category]

    # For percentages, calculate from totals rather than averaging averages
    if category.endswith("_pct"):
        made_col = category.replace("_pct", "_made")
        attempted_col = category.replace("_pct", "_attempted")
        avg_value_expr = f"CAST(SUM(pgs.{made_col}) AS REAL) / NULLIF(SUM(pgs.{attempted_col}), 0)"
    else:
        avg_value_expr = f"AVG(pgs.{stat_column})"

    return f"""
        SELECT
            p.player_id,
            p.first_name,
            p.last_name,
            p.team_id,
            p.position,
            p.jersey_number,
            p.height,
            p.weight,
            p.birth_date,
            p.country,
            p.draft_year,
            p.draft_round,
            p.draft_number,
            t.team_id as team_team_id,
            t.full_name as team_full_name,
            t.abbreviation as team_abbreviation,
            t.nickname as team_nickname,
            t.city as team_city,
            t.state as team_state,
            t.year_founded as team_year_founded,
            t.arena as team_arena,
            t.owner as team_owner,
            t.general_manager as team_general_manager,
            t.head_coach as team_head_coach,
            t.conference as team_conference,
            t.division as team_division,
            {avg_value_expr} as avg_value,
            COUNT(*) as games_played
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.player_id
        JOIN teams t ON pgs.team_id = t.team_id
        JOIN games g ON pgs.game_id = g.game_id
        WHERE g.season = ?
        GROUP BY
            p.player_id, p.first_name, p.last_name, p.team_id, p.position,
            p.jersey_number, p.height, p.weight, p.birth_date, p.country,
            p.draft_year, p.draft_round, p.draft_number,
            t.team_id, t.full_name, t.abbreviation, t.nickname, t.city,
            t.state, t.year_founded, t.arena, t.owner, t.general_manager,
            t.head_coach, t.conference, t.division
        HAVING COUNT(*) >= 10
        ORDER BY avg_value DESC
        LIMIT ?
    """


def _map_row_to_player(row: tuple) -> Player:
    """Map a database row to a Player model.

    Args:
        row: The database row tuple.

    Returns:
        A Player instance.
    """
    first_name = row[1]
    last_name = row[2]
    full_name = f"{first_name} {last_name}" if first_name and last_name else ""

    return Player(
        player_id=row[0],
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
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


def _map_row_to_team(row: tuple) -> Team:
    """Map a database row to a Team model.

    Args:
        row: The database row tuple starting at index 13.

    Returns:
        A Team instance.
    """
    return Team(
        team_id=row[13],
        full_name=row[14],
        abbreviation=row[15],
        nickname=row[16],
        city=row[17],
        state=row[18],
        year_founded=row[19],
        arena=row[20],
        owner=row[21],
        general_manager=row[22],
        head_coach=row[23],
        conference=row[24],
        division=row[25],
    )


def _map_row_to_leader_entry(row: tuple, rank: int) -> LeaderEntry:
    """Map a database row to a LeaderEntry model.

    Args:
        row: The database row tuple.
        rank: The ranking position.

    Returns:
        A LeaderEntry instance.
    """
    player = _map_row_to_player(row)
    team = _map_row_to_team(row)

    return LeaderEntry(
        rank=rank,
        player=player,
        team=team,
        value=round(row[26], 3),
        games=row[27],
    )


@router.get("/leaders", response_model=LeadersResponse)
async def get_league_leaders(
    request: Request,
    category: str = Query(
        ...,
        description="Statistical category (points, rebounds, assists, steals, blocks, fg_pct, fg3_pct, ft_pct)",
    ),
    season: int = Query(..., description="Season year (e.g., 2024)", ge=1946),
    limit: int = Query(10, description="Number of leaders to return (max 50)", ge=1, le=50),
) -> LeadersResponse | HTMLResponse:
    """Get league leaders for a specific statistical category.

    Returns the top players in a given statistical category for the specified season.
    Supports both JSON API responses and HTMX partial HTML rendering.

    Args:
        request: FastAPI request object.
        category: Statistical category to query.
        season: Season year to query.
        limit: Maximum number of leaders to return.

    Returns:
        LeadersResponse for API requests or HTMLResponse for HTMX requests.

    Raises:
        HTTPException: If category is invalid (400) or database query fails (500).
    """
    _validate_category(category)

    query = _build_leaders_query(category)

    try:
        results = execute_query(query, [season, limit])
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to query league leaders: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred while querying league leaders."
        ) from e

    # Build response using helper function
    leaders = [_map_row_to_leader_entry(row, idx) for idx, row in enumerate(results, start=1)]

    response_data = LeadersResponse(
        category=category,
        season=season,
        leaders=leaders,
    )

    # Check for HTMX request
    if is_htmx_request(request):
        templates = get_templates()
        return templates.TemplateResponse(
            "partials/leaders_table.html",
            {
                "request": request,
                "leaders": leaders,
                "category": category,
                "season": season,
            },
        )

    return response_data


def _validate_conference(conference: str | None) -> None:
    """Validate the conference filter.

    Args:
        conference: The conference to validate.

    Raises:
        HTTPException: If conference is invalid.
    """
    if conference and conference not in ("Eastern", "Western"):
        raise HTTPException(
            status_code=400, detail="Invalid conference. Must be 'Eastern' or 'Western'"
        )


def _build_standings_query(season: int, conference: str | None) -> tuple[str, list]:
    """Build the SQL query for team standings.

    Args:
        season: The season year.
        conference: Optional conference filter.

    Returns:
        A tuple of (query_string, params).
    """
    query = """
        SELECT
            t.team_id,
            t.full_name,
            t.abbreviation,
            t.nickname,
            t.city,
            t.state,
            t.year_founded,
            t.arena,
            t.owner,
            t.general_manager,
            t.head_coach,
            t.conference,
            t.division,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score > g.away_score)
                     OR (g.away_team_id = t.team_id AND g.away_score > g.home_score)
                THEN 1 ELSE 0
            END) as wins,
            SUM(CASE
                WHEN (g.home_team_id = t.team_id AND g.home_score < g.away_score)
                     OR (g.away_team_id = t.team_id AND g.away_score < g.home_score)
                THEN 1 ELSE 0
            END) as losses,
            SUM(CASE WHEN g.home_team_id = t.team_id AND g.home_score > g.away_score THEN 1 ELSE 0 END) as home_wins,
            SUM(CASE WHEN g.home_team_id = t.team_id AND g.home_score < g.away_score THEN 1 ELSE 0 END) as home_losses,
            SUM(CASE WHEN g.away_team_id = t.team_id AND g.away_score > g.home_score THEN 1 ELSE 0 END) as away_wins,
            SUM(CASE WHEN g.away_team_id = t.team_id AND g.away_score < g.home_score THEN 1 ELSE 0 END) as away_losses
        FROM teams t
        LEFT JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id)
            AND g.season = ?
            AND g.status = 'completed'
        WHERE 1=1
    """

    params: list = [season]

    if conference:
        query += " AND t.conference = ?"
        params.append(conference)

    query += """
        GROUP BY
            t.team_id, t.full_name, t.abbreviation, t.nickname, t.city,
            t.state, t.year_founded, t.arena, t.owner, t.general_manager,
            t.head_coach, t.conference, t.division
        ORDER BY
            t.conference, wins DESC
    """

    return query, params


def _calculate_win_percentage(wins: int, losses: int) -> float:
    """Calculate win percentage.

    Args:
        wins: Number of wins.
        losses: Number of losses.

    Returns:
        The win percentage (0.0 to 1.0).
    """
    total_games = wins + losses
    return wins / total_games if total_games > 0 else 0.0


def _build_record_string(wins: int, losses: int) -> str:
    """Build a record string from wins and losses.

    Args:
        wins: Number of wins.
        losses: Number of losses.

    Returns:
        The record string (e.g., "25-10").
    """
    return f"{wins}-{losses}"


class RankingTracker:
    """Helper class to track conference and division rankings."""

    def __init__(self) -> None:
        self.conference_rankings: dict[str, int] = {}
        self.division_rankings: dict[str, dict[str, int]] = {}

    def get_conference_rank(self, conference: str) -> int:
        """Get and increment the conference rank."""
        self.conference_rankings[conference] = self.conference_rankings.get(conference, 0) + 1
        return self.conference_rankings[conference]

    def get_division_rank(self, conference: str, division: str) -> int:
        """Get and increment the division rank."""
        if conference not in self.division_rankings:
            self.division_rankings[conference] = {}

        conf_div_ranks = self.division_rankings[conference]
        conf_div_ranks[division] = conf_div_ranks.get(division, 0) + 1
        return conf_div_ranks[division]


def _map_row_to_standings_entry(row: tuple, rankings: RankingTracker) -> StandingsEntry:
    """Map a database row to a StandingsEntry model.

    Args:
        row: The database row tuple.
        rankings: The ranking tracker instance.

    Returns:
        A StandingsEntry instance.
    """
    team = Team(
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

    wins = row[13] or 0
    losses = row[14] or 0
    home_wins = row[15] or 0
    home_losses = row[16] or 0
    away_wins = row[17] or 0
    away_losses = row[18] or 0

    win_pct = _calculate_win_percentage(wins, losses)

    # Calculate rankings
    conference_rank = rankings.get_conference_rank(team.conference)
    division_rank = rankings.get_division_rank(team.conference, team.division)

    return StandingsEntry(
        team=team,
        wins=wins,
        losses=losses,
        win_pct=round(win_pct, 3),
        home_record=_build_record_string(home_wins, home_losses),
        away_record=_build_record_string(away_wins, away_losses),
        division=team.division,
        conference_rank=conference_rank,
        division_rank=division_rank,
    )


@router.get("/standings", response_model=StandingsResponse)
async def get_standings(
    request: Request,
    season: int = Query(..., description="Season year (e.g., 2024)", ge=1946),
    conference: str | None = Query(None, description="Conference filter (Eastern or Western)"),
) -> StandingsResponse | HTMLResponse:
    """Get team standings for a specific season.

    Returns the win/loss records and rankings for all teams in the specified season.
    Supports both JSON API responses and HTMX partial HTML rendering.

    Args:
        request: FastAPI request object.
        season: Season year to query.
        conference: Optional conference filter (Eastern or Western).

    Returns:
        StandingsResponse for API requests or HTMLResponse for HTMX requests.

    Raises:
        HTTPException: If conference is invalid (400) or database query fails (500).
    """
    _validate_conference(conference)

    try:
        query, params = _build_standings_query(season, conference)
        results = execute_query(query, params)
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to query standings: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="An internal error occurred while querying standings."
        ) from e

    # Build standings with rankings
    rankings = RankingTracker()
    standings = [_map_row_to_standings_entry(row, rankings) for row in results]

    response_data = StandingsResponse(
        season=season,
        conference=conference,
        standings=standings,
    )

    # Check for HTMX request
    if is_htmx_request(request):
        templates = get_templates()
        return templates.TemplateResponse(
            "partials/standings_table.html",
            {
                "request": request,
                "standings": standings,
                "season": season,
                "conference": conference,
            },
        )

    return response_data
