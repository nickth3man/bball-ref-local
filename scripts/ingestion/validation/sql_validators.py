"""SQL-based validation queries for data integrity checks.

This module contains SQL queries used for validating data integrity
across the basketball database. These queries can be used standalone
or through the DataValidator class.
"""

# =============================================================================
# Points Calculation Validation
# =============================================================================

VALIDATE_POINTS_CALCULATION = """
SELECT 
    player_id,
    game_id,
    points,
    (field_goals_made * 2 + three_pointers_made + free_throws_made) as calc_points,
    ABS(points - (field_goals_made * 2 + three_pointers_made + free_throws_made)) as diff
FROM player_game_statistics
WHERE ABS(points - (field_goals_made * 2 + three_pointers_made + free_throws_made)) > 0
LIMIT 100;
"""

VALIDATE_POINTS_CALCULATION_SEASON = """
SELECT 
    player_id,
    season,
    points,
    (field_goals_made * 2 + three_pointers_made + free_throws_made) as calc_points,
    ABS(points - (field_goals_made * 2 + three_pointers_made + free_throws_made)) as diff
FROM player_season_totals
WHERE ABS(points - (field_goals_made * 2 + three_pointers_made + free_throws_made)) > 0
LIMIT 100;
"""

# =============================================================================
# Game Winner Validation
# =============================================================================

VALIDATE_GAME_WINNERS = """
SELECT 
    game_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    winner_team_id,
    CASE 
        WHEN home_score > away_score THEN home_team_id
        WHEN away_score > home_score THEN away_team_id
        ELSE NULL
    END as calculated_winner
FROM games
WHERE winner_team_id IS NOT NULL
  AND winner_team_id != CASE 
        WHEN home_score > away_score THEN home_team_id
        WHEN away_score > home_score THEN away_team_id
        ELSE NULL
    END;
"""

VALIDATE_GAME_TIES = """
SELECT 
    game_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    winner_team_id
FROM games
WHERE home_score = away_score
  AND winner_team_id IS NOT NULL;
"""

# =============================================================================
# Foreign Key Validation
# =============================================================================

VALIDATE_FOREIGN_KEYS_PLAYERS = """
SELECT 
    pgs.person_id as player_id,
    COUNT(*) as orphan_count
FROM player_game_statistics pgs
LEFT JOIN player_master p ON pgs.person_id = p.player_id
WHERE p.player_id IS NULL
GROUP BY pgs.person_id
ORDER BY orphan_count DESC;
"""

VALIDATE_FOREIGN_KEYS_TEAMS = """
SELECT 
    pgs.player_team_city || ' ' || pgs.player_team_name as team_identifier,
    COUNT(*) as orphan_count
FROM player_game_statistics pgs
LEFT JOIN team_abbreviations t ON pgs.player_team_city = t.team_city AND pgs.player_team_name = t.team_name
WHERE t.team_id IS NULL
GROUP BY pgs.player_team_city, pgs.player_team_name
ORDER BY orphan_count DESC;
"""

VALIDATE_FOREIGN_KEYS_GAMES = """
SELECT 
    pgs.game_id,
    COUNT(*) as orphan_count
FROM player_game_statistics pgs
LEFT JOIN games_historical g ON pgs.game_id = g.game_id
WHERE g.game_id IS NULL
GROUP BY pgs.game_id
ORDER BY orphan_count DESC;
"""

VALIDATE_FOREIGN_KEYS_SEASONS = """
SELECT 
    pss.season,
    COUNT(*) as orphan_count
FROM player_season_totals pss
LEFT JOIN games_historical g ON CAST(SUBSTRING(CAST(g.game_id AS VARCHAR), 1, 4) AS INTEGER) = pss.season
WHERE g.game_id IS NULL
GROUP BY pss.season
ORDER BY orphan_count DESC;
"""

# =============================================================================
# Duplicate Validation
# =============================================================================

VALIDATE_DUPLICATE_PLAYERS = """
SELECT 
    player_id,
    COUNT(*) as duplicate_count
FROM player_master
GROUP BY player_id
HAVING COUNT(*) > 1;
"""

VALIDATE_DUPLICATE_GAMES = """
SELECT 
    game_id,
    COUNT(*) as duplicate_count
FROM games_historical
GROUP BY game_id
HAVING COUNT(*) > 1;
"""

VALIDATE_DUPLICATE_PLAYER_GAMES = """
SELECT 
    person_id as player_id,
    game_id,
    COUNT(*) as duplicate_count
FROM player_game_statistics
GROUP BY person_id, game_id
HAVING COUNT(*) > 1;
"""

# =============================================================================
# Season Range Validation
# =============================================================================

VALIDATE_SEASON_RANGES = """
SELECT 
    season,
    MIN(season) as year_start,
    MAX(season) as year_end
FROM player_season_totals
GROUP BY season
HAVING season < 1946 
   OR season > 2030;
"""

VALIDATE_PLAYER_CAREER_SEASONS = """
SELECT 
    player_id,
    player as full_name,
    draft_year,
    from_year as career_start,
    to_year as career_end
FROM player_master
WHERE from_year < 1946 
   OR (to_year IS NOT NULL AND to_year > 2030)
   OR (to_year IS NOT NULL AND to_year < from_year);
"""

# =============================================================================
# Statistics Percentage Validation
# =============================================================================

VALIDATE_STAT_PERCENTAGES = """
SELECT 
    player_id,
    season,
    field_goal_pct as fg_pct,
    three_point_pct as fg3_pct,
    free_throw_pct as ft_pct
FROM player_season_totals
WHERE field_goal_pct < 0 OR field_goal_pct > 1
   OR three_point_pct < 0 OR three_point_pct > 1
   OR free_throw_pct < 0 OR free_throw_pct > 1
LIMIT 100;
"""

VALIDATE_STAT_PERCENTAGES_GAME = """
SELECT 
    person_id as player_id,
    game_id,
    field_goal_pct as fg_pct,
    three_point_pct as fg3_pct,
    free_throw_pct as ft_pct
FROM player_game_statistics
WHERE field_goal_pct < 0 OR field_goal_pct > 1
   OR three_point_pct < 0 OR three_point_pct > 1
   OR free_throw_pct < 0 OR free_throw_pct > 1
LIMIT 100;
"""

# =============================================================================
# Game Scores Validation
# =============================================================================

VALIDATE_GAME_SCORES = """
SELECT 
    game_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score
FROM games_historical
WHERE home_score < 0 
   OR away_score < 0
   OR home_score > 200
   OR away_score > 200;
"""

VALIDATE_GAME_QUARTER_SUMS = """
SELECT 
    game_id,
    team_score as home_score,
    q1_points + q2_points + q3_points + q4_points + COALESCE(ot_points, 0) as calc_score,
    opponent_score as away_score
FROM team_game_statistics
WHERE q1_points IS NOT NULL
  AND team_score != q1_points + q2_points + q3_points + q4_points + COALESCE(ot_points, 0);
"""

# =============================================================================
# Player Age Validation
# =============================================================================

VALIDATE_PLAYER_AGES = """
SELECT 
    p.player_id,
    p.player as full_name,
    p.birth_date,
    pss.season,
    EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM p.birth_date) as calculated_age
FROM player_master p
JOIN player_season_totals pss ON p.player_id = pss.player_id
WHERE p.birth_date IS NOT NULL
  AND (
      EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM p.birth_date) < 15 
      OR EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM p.birth_date) > 50
  );
"""

VALIDATE_PLAYER_CAREER_SPAN = """
SELECT 
    player_id,
    player as full_name,
    birth_date,
    from_year as career_start,
    to_year as career_end,
    CASE 
        WHEN to_year IS NOT NULL THEN to_year - EXTRACT(YEAR FROM birth_date)
        ELSE EXTRACT(YEAR FROM CURRENT_DATE) - EXTRACT(YEAR FROM birth_date)
    END as age_at_career_end
FROM player_master
WHERE birth_date IS NOT NULL
  AND (
      from_year - EXTRACT(YEAR FROM birth_date) < 18
      OR (to_year IS NOT NULL AND to_year - EXTRACT(YEAR FROM birth_date) > 50)
  );
"""

# =============================================================================
# Team Season Continuity
# =============================================================================

VALIDATE_TEAM_SEASON_CONTINUITY = """
WITH team_seasons AS (
    SELECT 
        team_id,
        season as season_year
    FROM team_season_totals
    GROUP BY team_id, season
),
season_gaps AS (
    SELECT 
        team_id,
        season_year,
        LAG(season_year) OVER (PARTITION BY team_id ORDER BY season_year) as prev_season
    FROM team_seasons
)
SELECT 
    team_id,
    season_year,
    prev_season,
    season_year - prev_season as gap
FROM season_gaps
WHERE prev_season IS NOT NULL
  AND season_year - prev_season > 1
ORDER BY team_id, season_year;
"""

VALIDATE_TEAM_ACTIVE_YEARS = """
SELECT 
    t.team_id,
    t.team_city || ' ' || t.team_name as full_name,
    MIN(t.season_active_from) as year_founded,
    MIN(tss.season) as first_season,
    MAX(tss.season) as last_season
FROM team_abbreviations t
LEFT JOIN team_season_totals tss ON t.team_id = tss.team_id
WHERE tss.season IS NOT NULL
GROUP BY t.team_id, t.team_city, t.team_name
HAVING MIN(tss.season) < MIN(t.season_active_from)
   OR MAX(tss.season) > EXTRACT(YEAR FROM CURRENT_DATE);
"""
