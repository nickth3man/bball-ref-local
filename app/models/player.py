"""Player Pydantic models for basketball statistics."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Player(BaseModel):
    """Player model representing a basketball player.

    Attributes:
        player_id: Unique identifier for the player.
        first_name: Player's first name.
        last_name: Player's last name.
        full_name: Player's full name.
        team_id: ID of the player's current team.
        position: Player's position (PG, SG, SF, PF, C, G, F, etc.).
        jersey_number: Player's jersey number.
        height: Player's height as string (e.g., "6-9").
        height_cm: Player's height in centimeters.
        weight: Player's weight in pounds.
        weight_kg: Player's weight in kilograms.
        birth_date: Player's date of birth.
        birth_place: Player's place of birth.
        birth_country: Player's country of birth.
        country: Player's country of origin.
        college: Player's college.
        draft_year: Year the player was drafted (None if undrafted).
        draft_round: Round the player was drafted (None if undrafted).
        draft_number: Overall pick number (None if undrafted).
        draft_team_id: ID of the team that drafted the player.
        shoots: Player's shooting hand (L or R).
        active: Whether the player is currently active.
        hall_of_fame: Whether the player is in the Hall of Fame.
    """

    model_config = ConfigDict(from_attributes=True)

    player_id: str = Field(description="Unique identifier for the player")
    first_name: str = Field(description="Player's first name")
    last_name: str = Field(description="Player's last name")
    full_name: str = Field(description="Player's full name")
    team_id: str = Field(description="ID of the player's current team")
    position: str | None = Field(
        default=None,
        description="Player's position (PG, SG, SF, PF, C, G, F)",
        pattern=r"^(PG|SG|SF|PF|C|G|F)?$",
    )
    jersey_number: int | None = Field(
        default=None, description="Player's jersey number", ge=0, le=99
    )
    height: str | None = Field(default=None, description="Player's height (e.g., 6-9)")
    height_cm: int | None = Field(default=None, description="Player's height in centimeters", gt=0)
    weight: int | None = Field(default=None, description="Player's weight in pounds", gt=0)
    weight_kg: int | None = Field(default=None, description="Player's weight in kilograms", gt=0)
    birth_date: date | None = Field(default=None, description="Player's date of birth")
    birth_place: str | None = Field(default=None, description="Player's place of birth")
    birth_country: str | None = Field(default=None, description="Player's country of birth")
    country: str | None = Field(default=None, description="Player's country of origin")
    college: str | None = Field(default=None, description="Player's college")
    draft_year: int | None = Field(default=None, description="Year the player was drafted", ge=1946)
    draft_round: int | None = Field(
        default=None, description="Round the player was drafted", ge=1, le=3
    )
    draft_number: int | None = Field(default=None, description="Overall pick number", ge=1, le=60)
    draft_team_id: str | None = Field(
        default=None, description="ID of the team that drafted the player"
    )
    shoots: str | None = Field(
        default=None, description="Player's shooting hand (L or R)", pattern=r"^(L|R)?$"
    )
    active: bool = Field(default=True, description="Whether the player is currently active")
    hall_of_fame: bool = Field(
        default=False, description="Whether the player is in the Hall of Fame"
    )

    @property
    def height_display(self) -> str | None:
        """
        Format the player's height as a feet-inches string.

        Returns:
            str: Height formatted as "F-I" (feet-inches), where inches are 0–11 (e.g., "6-9"), or `None` if `height` is not set.
        """
        return self.height

    @property
    def weight_display(self) -> str | None:
        """
        Format the player's weight with units.

        Returns:
            str: Weight formatted with lbs, or `None` if `weight` is not set.
        """
        if self.weight is None:
            return None
        return f"{self.weight} lbs"
