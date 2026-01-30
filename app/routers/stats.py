"""Stats API router for league leaders and standings.

Provides endpoints for retrieving league statistical leaders and team standings
for a given season.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from app.models.player import Player
from app.models.team import Team
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.services.database import execute_query

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

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
    # Validate category
    if category not in VALID_CATEGORIES:
        valid_list = ", ".join(sorted(VALID_CATEGORIES))
        raise HTTPException(
            status_code=400, detail=f"Invalid category '{category}'. Valid categories: {valid_list}"
        )

    # Build and execute query
    stat_column = CATEGORY_COLUMN_MAP[category]

    try:
        query = f"""
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
                AVG(pgs.{stat_column}) as avg_value,
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

        results = execute_query(query, [season, limit])

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query league leaders: {str(e)}")

    # Build response
    leaders = []
    for idx, row in enumerate(results, start=1):
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

        team = Team(
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

        leaders.append(
            LeaderEntry(
                rank=idx,
                player=player,
                team=team,
                value=round(row[26], 3),
                games=row[27],
            )
        )

    response_data = LeadersResponse(
        category=category,
        season=season,
        leaders=leaders,
    )

    # Check for HTMX request
    if request.headers.get("HX-Request"):
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
    # Validate conference if provided
    if conference and conference not in ("Eastern", "Western"):
        raise HTTPException(
            status_code=400, detail="Invalid conference. Must be 'Eastern' or 'Western'"
        )

    try:
        # Base query for team standings
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

        results = execute_query(query, params)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query standings: {str(e)}")

    # Build standings with rankings
    standings = []
    conference_rankings: dict[str, int] = {}
    division_rankings: dict[str, int] = {}

    for row in results:
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

        total_games = wins + losses
        win_pct = wins / total_games if total_games > 0 else 0.0

        # Calculate rankings
        conf_key = team.conference
        div_key = f"{team.conference}_{team.division}"

        conference_rankings[conf_key] = conference_rankings.get(conf_key, 0) + 1
        division_rankings[div_key] = division_rankings.get(div_key, 0) + 1

        standings.append(
            StandingsEntry(
                team=team,
                wins=wins,
                losses=losses,
                win_pct=round(win_pct, 3),
                home_record=f"{home_wins}-{home_losses}",
                away_record=f"{away_wins}-{away_losses}",
                division=team.division,
                conference_rank=conference_rankings[conf_key],
                division_rank=division_rankings[div_key],
            )
        )

    response_data = StandingsResponse(
        season=season,
        conference=conference,
        standings=standings,
    )

    # Check for HTMX request
    if request.headers.get("HX-Request"):
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
