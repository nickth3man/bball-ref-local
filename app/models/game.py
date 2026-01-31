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
        is_overtime: Whether the game went to overtime.
    """

    #

    model_config = ConfigDict(from_attributes=True)

    game_id: str = Field(description="Unique identifier for the game")
    season: int = Field(description="NBA season year (e.g., 2024 for 2023-24 season)", ge=1946)
    season_type: str = Field(
        description="Type of season (Regular Season or Playoffs)",
        pattern=r"^(Regular Season|Playoffs)$",
    )
    game_date: date = Field(description="Date when the game is/was played")
    home_team_id: str = Field(description="ID of the home team")
    away_team_id: str = Field(description="ID of the away team")
    home_score: int | None = Field(default=None, description="Final score for the home team", ge=0)
    away_score: int | None = Field(default=None, description="Final score for the away team", ge=0)
    winner_team_id: str | None = Field(
        default=None, description="ID of the winning team (None if game not completed)"
    )
    status: str = Field(
        default="scheduled",
        description="Current status of the game",
        pattern=r"^(scheduled|live|final)$",
    )
    is_overtime: bool = Field(
        default=False,
        description="Whether the game went to overtime",
    )

    @property
    def is_completed(self) -> bool:
        """
        Determine whether the game is completed.

        Returns:
            `true` if the game's status equals "final", `false` otherwise.
        """
        return self.status == "final"

    @property
    def is_live(self) -> bool:
        """
        Indicates whether the game's status is live.

        Returns:
            `true` if the game status is "live", `false` otherwise.
        """
        return self.status == "live"

    @property
    def point_differential(self) -> int | None:
        """
        Point difference between the home and away teams (absolute value).

        Returns:
            int: Absolute difference between `home_score` and `away_score`, or `None` if either score is missing.
            Use this for display purposes (margin of victory).
        """
        if self.home_score is None or self.away_score is None:
            return None
        return abs(self.home_score - self.away_score)

    @property
    def home_point_differential(self) -> int | None:
        """
        Point differential from the home team's perspective (signed value).

        Returns:
            int: `home_score - away_score`, or `None` if either score is missing.
            Positive values mean home team won, negative means away team won.
            Use this for analytical purposes where signed direction matters.
        """
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score - self.away_score

    @property
    def winning_team_name(self) -> str | None:
        """
        Return which side won the game ("home" or "away").

        Returns:
            str | None: "home" if the home team won, "away" if the away team won, or None if the game is not completed or the winner is unknown.
        """
        if not self.is_completed or self.winner_team_id is None:
            return None
        if self.winner_team_id == self.home_team_id:
            return "home"
        return "away"
