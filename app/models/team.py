"""Team Pydantic models for basketball statistics."""


from pydantic import BaseModel, ConfigDict, Field


class Team(BaseModel):
    """Team model representing a basketball team.

    Attributes:
        team_id: Unique identifier for the team.
        full_name: Full official name of the team.
        abbreviation: Team abbreviation (e.g., 'LAL', 'BOS').
        nickname: Team nickname (e.g., 'Lakers', 'Celtics').
        city: City where the team is based.
        state: State where the team is based.
        year_founded: Year the team was founded.
        arena: Name of the team's home arena.
        owner: Team owner or ownership group.
        general_manager: Team's general manager.
        head_coach: Team's head coach.
        conference: Conference (Eastern or Western).
        division: Division within the conference.
    """

    model_config = ConfigDict(from_attributes=True)

    team_id: int = Field(description="Unique identifier for the team")
    full_name: str = Field(description="Full official name of the team")
    abbreviation: str = Field(
        description="Team abbreviation (e.g., 'LAL', 'BOS')",
        min_length=2,
        max_length=3
    )
    nickname: str = Field(description="Team nickname (e.g., 'Lakers', 'Celtics')")
    city: str = Field(description="City where the team is based")
    state: str | None = Field(
        default=None,
        description="State where the team is based"
    )
    year_founded: int | None = Field(
        default=None,
        description="Year the team was founded",
        ge=1946
    )
    arena: str | None = Field(
        default=None,
        description="Name of the team's home arena"
    )
    owner: str | None = Field(
        default=None,
        description="Team owner or ownership group"
    )
    general_manager: str | None = Field(
        default=None,
        description="Team's general manager"
    )
    head_coach: str | None = Field(
        default=None,
        description="Team's head coach"
    )
    conference: str = Field(
        description="Conference (Eastern or Western)",
        pattern=r"^(Eastern|Western)$"
    )
    division: str = Field(
        description="Division within the conference",
        pattern=r"^(Atlantic|Central|Southeast|Northwest|Pacific|Southwest)$"
    )

    @property
    def display_name(self) -> str:
        """Return formatted team name (City Nickname)."""
        return f"{self.city} {self.nickname}"
