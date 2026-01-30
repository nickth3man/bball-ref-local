"""Player Pydantic models for basketball statistics."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Player(BaseModel):
    """Player model representing a basketball player.

    Attributes:
        player_id: Unique identifier for the player.
        first_name: Player's first name.
        last_name: Player's last name.
        team_id: ID of the player's current team.
        position: Player's position (PG, SG, SF, PF, C).
        jersey_number: Player's jersey number.
        height: Player's height in inches.
        weight: Player's weight in pounds.
        birth_date: Player's date of birth.
        country: Player's country of origin.
        draft_year: Year the player was drafted (None if undrafted).
        draft_round: Round the player was drafted (None if undrafted).
        draft_number: Overall pick number (None if undrafted).
    """

    model_config = ConfigDict(from_attributes=True)

    player_id: int = Field(description="Unique identifier for the player")
    first_name: str = Field(description="Player's first name")
    last_name: str = Field(description="Player's last name")
    team_id: int = Field(description="ID of the player's current team")
    position: str = Field(
        description="Player's position (PG, SG, SF, PF, C)",
        pattern=r"^(PG|SG|SF|PF|C)$"
    )
    jersey_number: int | None = Field(
        default=None,
        description="Player's jersey number",
        ge=0,
        le=99
    )
    height: int | None = Field(
        default=None,
        description="Player's height in inches",
        gt=0
    )
    weight: int | None = Field(
        default=None,
        description="Player's weight in pounds",
        gt=0
    )
    birth_date: date | None = Field(
        default=None,
        description="Player's date of birth"
    )
    country: str | None = Field(
        default=None,
        description="Player's country of origin"
    )
    draft_year: int | None = Field(
        default=None,
        description="Year the player was drafted",
        ge=1946
    )
    draft_round: int | None = Field(
        default=None,
        description="Round the player was drafted",
        ge=1,
        le=3
    )
    draft_number: int | None = Field(
        default=None,
        description="Overall pick number",
        ge=1,
        le=60
    )

    @property
    def full_name(self) -> str:
        """Return the player's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def height_display(self) -> str | None:
        """Return height in feet-inches format (e.g., '6-9')."""
        if self.height is None:
            return None
        feet = self.height // 12
        inches = self.height % 12
        return f"{feet}-{inches}"
