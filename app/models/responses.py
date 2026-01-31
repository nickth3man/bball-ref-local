"""Response models for API pagination and error handling.

This module provides reusable response models for paginated API responses
and consistent error formatting.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.game import Game
from app.models.player import Player
from app.models.stats import PlayerGameStats
from app.models.team import Team


class PaginatedResponse[T](BaseModel):
    """Generic paginated response model.

    Attributes:
        items: List of items for the current page.
        total: Total count of all items across all pages.
        page: Current page number (1-indexed).
        page_size: Number of items per page.
        pages: Calculated total number of pages.
    """

    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(description="List of items for the current page")
    total: int = Field(description="Total count of all items across all pages", ge=0)
    page: int = Field(description="Current page number (1-indexed)", ge=1)
    page_size: int = Field(description="Number of items per page", ge=1)
    pages: int = Field(description="Calculated total number of pages", ge=0)


class PlayerListResponse(PaginatedResponse[Player]):
    """Paginated response for player lists.

    Attributes:
        items: List of Player objects.
        total: Total count of all players.
        page: Current page number (1-indexed).
        page_size: Number of players per page.
        pages: Calculated total number of pages.
    """

    pass


class TeamListResponse(PaginatedResponse[Team]):
    """Paginated response for team lists.

    Attributes:
        items: List of Team objects.
        total: Total count of all teams.
        page: Current page number (1-indexed).
        page_size: Number of teams per page.
        pages: Calculated total number of pages.
    """

    pass


class GameListResponse(PaginatedResponse[Game]):
    """Paginated response for game lists.

    Attributes:
        items: List of Game objects.
        total: Total count of all games.
        page: Current page number (1-indexed).
        page_size: Number of games per page.
        pages: Calculated total number of pages.
    """

    pass


class PlayerGameStatsListResponse(PaginatedResponse[PlayerGameStats]):
    """Paginated response for player game statistics lists.

    Attributes:
        items: List of PlayerGameStats objects.
        total: Total count of all stat records.
        page: Current page number (1-indexed).
        page_size: Number of stat records per page.
        pages: Calculated total number of pages.
    """

    pass


class APIErrorResponse(BaseModel):
    """Consistent error response model for API errors.

    Attributes:
        error_code: Machine-readable error code identifier.
        message: Human-readable error description.
        details: Additional error details or context (optional).
    """

    model_config = ConfigDict(from_attributes=True)

    error_code: str = Field(description="Machine-readable error code identifier")
    message: str = Field(description="Human-readable error description")
    details: dict[str, Any] | None = Field(
        default=None, description="Additional error details or context"
    )


class PaginationParams(BaseModel):
    """Query parameter validation for pagination.

    Attributes:
        page: Page number to retrieve (1-indexed, defaults to 1).
        page_size: Number of items per page (defaults to 20, max 100).
    """

    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, description="Page number to retrieve (1-indexed)", ge=1)
    page_size: int = Field(
        default=20,
        description="Number of items per page",
        ge=1,
        le=100,
    )
