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

    TODO: MEDIUM - Add quarter score fields if needed for box score display
    Current database schema includes quarter scores but not in this model:
      - home_q1, home_q2, home_q3, home_q4, home_ot
      - away_q1, away_q2, away_q3, away_q4, away_ot
    However, these fields are often NULL in ETL (see TODO in etl_games.py)

    TODO: MEDIUM - Add is_overtime flag to model
    Database has this field but it's not in the Pydantic model.
    Currently hardcoded to False in etl_games.py

    TODO: MEDIUM - Add arena and attendance fields
    Present in database schema but not populated by ETL
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
        Point difference between the home and away teams.

        Returns:
            int: Absolute difference between `home_score` and `away_score`, or `None` if either score is missing.

        TODO: MEDIUM - Consider adding signed point differential variant
        Current implementation returns abs() which loses information about which team won.
        Options:
          1. Keep as-is for display purposes (margin of victory)
          2. Add home_point_differential property (home_score - away_score)
          3. Add away_point_differential property
        Note: winning_team_name property already provides winner information
        """
        if self.home_score is None or self.away_score is None:
            return None
        return abs(self.home_score - self.away_score)

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
