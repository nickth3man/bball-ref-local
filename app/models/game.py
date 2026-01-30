"""Game Pydantic models for basketball statistics."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Game(BaseModel):
    """Game model representing a basketball game.

    Attributes:
        game_id: Unique identifier for the game.
        season: NBA season year (e.g., 2024 for 2023-24 season).
        season_type: Type of season (Regular Season or Playoffs).
        game_date: Date when the game is/was played.
        home_team_id: ID of the home team.
        away_team_id: ID of the away team.
        home_score: Final score for the home team.
        away_score: Final score for the away team.
        winner_team_id: ID of the winning team (None if game not completed).
        status: Current status of the game (scheduled, live, final).
    """

    model_config = ConfigDict(from_attributes=True)

    game_id: str = Field(description="Unique identifier for the game")
    season: int = Field(
        description="NBA season year (e.g., 2024 for 2023-24 season)",
        ge=1946
    )
    season_type: str = Field(
        description="Type of season (Regular Season or Playoffs)",
        pattern=r"^(Regular Season|Playoffs)$"
    )
    game_date: date = Field(description="Date when the game is/was played")
    home_team_id: int = Field(description="ID of the home team")
    away_team_id: int = Field(description="ID of the away team")
    home_score: int | None = Field(
        default=None,
        description="Final score for the home team",
        ge=0
    )
    away_score: int | None = Field(
        default=None,
        description="Final score for the away team",
        ge=0
    )
    winner_team_id: int | None = Field(
        default=None,
        description="ID of the winning team (None if game not completed)"
    )
    status: str = Field(
        default="scheduled",
        description="Current status of the game",
        pattern=r"^(scheduled|live|final)$"
    )

    @property
    def is_completed(self) -> bool:
        """Check if the game has been completed."""
        return self.status == "final"

    @property
    def is_live(self) -> bool:
        """Check if the game is currently live."""
        return self.status == "live"

    @property
    def point_differential(self) -> int | None:
        """Return the point differential (None if game not completed)."""
        if self.home_score is None or self.away_score is None:
            return None
        return abs(self.home_score - self.away_score)

    @property
    def winning_team_name(self) -> str | None:
        """Return 'home' or 'away' for the winning team."""
        if not self.is_completed or self.winner_team_id is None:
            return None
        if self.winner_team_id == self.home_team_id:
            return "home"
        return "away"
