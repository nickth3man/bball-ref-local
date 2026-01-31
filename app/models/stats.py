"""Statistics Pydantic models for basketball player game stats."""

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PlayerGameStats(BaseModel):
    """PlayerGameStats model representing a player's statistics for a single game.

    Attributes:
        stat_id: Unique identifier for the stat record.
        game_id: ID of the game.
        player_id: ID of the player.
        team_id: ID of the team the player was on for this game.
        minutes_played: Minutes played in the game.
        points: Total points scored.
        rebounds_offensive: Offensive rebounds.
        rebounds_defensive: Defensive rebounds.
        assists: Total assists.
        steals: Total steals.
        blocks: Total blocks.
        turnovers: Total turnovers.
        personal_fouls: Total personal fouls.
        fg_made: Field goals made.
        fg_attempted: Field goals attempted.
        fg3_made: Three-point field goals made.
        fg3_attempted: Three-point field goals attempted.
        ft_made: Free throws made.
        ft_attempted: Free throws attempted.
    """

    model_config = ConfigDict(from_attributes=True)

    stat_id: int = Field(description="Unique identifier for the stat record")
    game_id: str = Field(description="ID of the game")
    player_id: str = Field(description="ID of the player")
    team_id: str = Field(description="ID of the team the player was on for this game")
    minutes_played: float | None = Field(
        default=None, description="Minutes played in the game", ge=0
    )
    points: int = Field(default=0, description="Total points scored", ge=0)
    rebounds_offensive: int = Field(default=0, description="Offensive rebounds", ge=0)
    rebounds_defensive: int = Field(default=0, description="Defensive rebounds", ge=0)
    assists: int = Field(default=0, description="Total assists", ge=0)
    steals: int = Field(default=0, description="Total steals", ge=0)
    blocks: int = Field(default=0, description="Total blocks", ge=0)
    turnovers: int = Field(default=0, description="Total turnovers", ge=0)
    personal_fouls: int = Field(default=0, description="Total personal fouls", ge=0)
    fg_made: int = Field(default=0, description="Field goals made", ge=0)
    fg_attempted: int = Field(default=0, description="Field goals attempted", ge=0)
    fg3_made: int = Field(default=0, description="Three-point field goals made", ge=0)
    fg3_attempted: int = Field(default=0, description="Three-point field goals attempted", ge=0)
    ft_made: int = Field(default=0, description="Free throws made", ge=0)
    ft_attempted: int = Field(default=0, description="Free throws attempted", ge=0)

    @computed_field
    @property
    def rebounds_total(self) -> int:
        """
        Total rebounds for the game.

        Returns:
            total_rebounds (int): Sum of offensive and defensive rebounds.
        """
        return self.rebounds_offensive + self.rebounds_defensive

    @computed_field
    @property
    def fg_pct(self) -> float | None:
        """
        Compute the player's field goal percentage on a 0–1 scale.

        Returns:
            float | None: Field goal percentage rounded to three decimals, or `None` if `fg_attempted` is 0.
        """
        if self.fg_attempted == 0:
            return None
        return round(self.fg_made / self.fg_attempted, 3)

    @computed_field
    @property
    def fg3_pct(self) -> float | None:
        """
        Three-point field goal percentage on a 0-1 scale, rounded to three decimals.

        Returns:
            fg3_pct (float | None): The three-point field goal percentage (0.0–1.0) rounded to three decimals, or `None` if `fg3_attempted` is 0.
        """
        if self.fg3_attempted == 0:
            return None
        return round(self.fg3_made / self.fg3_attempted, 3)

    @computed_field
    @property
    def ft_pct(self) -> float | None:
        """
        Return the free throw shooting percentage on a 0-1 scale.

        Returns:
            float | None: Free throw percentage rounded to three decimal places if free throws were attempted; `None` if `ft_attempted` is 0.
        """
        if self.ft_attempted == 0:
            return None
        return round(self.ft_made / self.ft_attempted, 3)

    @computed_field
    @property
    def effective_fg_pct(self) -> float | None:
        """
        Calculate the effective field goal percentage, weighting three-pointers as 1.5 field goals.

        Returns:
            float | None: Effective field goal percentage rounded to 3 decimals, or `None` if `fg_attempted` is 0.
        """
        if self.fg_attempted == 0:
            return None
        return round((self.fg_made + 0.5 * self.fg3_made) / self.fg_attempted, 3)

    @computed_field
    @property
    def true_shooting_pct(self) -> float | None:
        """
        Calculate the player's true shooting percentage.

        Returns:
            float | None: True shooting percentage rounded to three decimals, or `None` if both field-goal attempts and free-throw attempts are zero (calculation not feasible).

        Formula verified correct per basketball-reference.com:
            TS% = PTS / (2 * (FGA + 0.44 * FTA))
        Where:
            - PTS = Total points scored
            - FGA = Field goal attempts
            - FTA = Free throw attempts
            - 0.44 = Coefficient accounting for non-possession-ending FTs
        """
        fga = self.fg_attempted
        fta = self.ft_attempted
        if fga == 0 and fta == 0:
            return None
        ts_attempts = 2 * (fga + 0.44 * fta)
        if ts_attempts == 0:
            return None
        return round(self.points / ts_attempts, 3)

    # TODO: MEDIUM - Add computed fields for 2-point statistics
    # These are commonly displayed alongside other shooting stats
    #
    # @computed_field
    # @property
    # def two_fg_made(self) -> int:
    #     """Two-point field goals made: FG - 3P"""
    #     return self.fg_made - self.fg3_made
    #
    # @computed_field
    # @property
    # def two_fg_attempted(self) -> int:
    #     """Two-point field goals attempted: FGA - 3PA"""
    #     return self.fg_attempted - self.fg3_attempted
    #
    # @computed_field
    # @property
    # def two_fg_pct(self) -> float | None:
    #     """Two-point field goal percentage: 2P / 2PA"""
    #     if self.two_fg_attempted == 0:
    #         return None
    #     return round(self.two_fg_made / self.two_fg_attempted, 3)
    #
    # Note: Add corresponding columns to player_game_stats table if needed

    @computed_field
    @property
    def plus_minus(self) -> int | None:
        """
        Represents the player's plus/minus for the game, if available.

        Returns:
            int | None: The player's plus/minus value for the game, or `None` when the statistic is not available.

        TODO: HIGH - Implement plus/minus from data source
        Issue: This currently always returns None as a placeholder
        Options:
          1. Fetch from NBA API PlayerGameLogs endpoint (includes PLUS_MINUS field)
          2. Calculate from play-by-play data (if available)
          3. Remove this computed field and use database column directly
        Related: player_game_logs table has plus_minus column but not populated by ETL
          - See TODO in scripts/etl_stats.py
        Priority: MEDIUM
        """
        # This would typically come from the data source
        # Returning None as it's not in the base attributes
        return None
