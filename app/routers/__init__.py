from app.routers.players import router as players_router
from app.routers.teams import router as teams_router
from app.routers.games import router as games_router
from app.routers.stats import router as stats_router

__all__ = ["players_router", "teams_router", "games_router", "stats_router"]
