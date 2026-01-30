# Product Requirements Document
## Basketball-Reference.com Clone
### Project Codename: HoopsDB

**Version 1.0** | **Last Updated:** January 2026  
**Status:** Final

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema](#4-database-schema)
5. [Feature Requirements](#5-feature-requirements)
6. [UI/UX Design Guidelines](#6-uiux-design-guidelines)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Data Strategy](#8-data-strategy)
9. [Project Structure](#9-project-structure)
10. [Appendix](#10-appendix)

---

## 1. Executive Summary

### 1.1 Objective
Build a comprehensive, local-first basketball statistics web application that replicates the core functionality of basketball-reference.com using 100% open-source technologies.

### 1.2 Core Philosophy
- **Simplicity**: Minimal dependencies, easy local setup
- **Performance**: Fast analytical queries via DuckDB
- **Data Completeness**: Historical NBA data from 1946 to present
- **Zero Cost**: 100% open-source stack, no external API keys required
- **Incremental Delivery**: Phased rollout starting with core features

### 1.3 Target Audience
- Basketball fans and enthusiasts
- Sports analysts and researchers
- Fantasy basketball players
- Journalists and content creators
- Data scientists and hobbyists

---

## 2. Project Overview

### 2.1 Purpose
Create a fully functional basketball statistics platform providing comprehensive NBA historical and current season data, including player statistics, team information, game logs, standings, and advanced analytics.

### 2.2 Goals and Objectives
- Provide fast, searchable access to player and team statistics
- Support multiple statistical views (per game, totals, advanced metrics)
- Enable historical data analysis across all NBA seasons (1946-present)
- Deliver a responsive, user-friendly interface
- Maintain 100% open-source stack with minimal dependencies
- Support automated daily data updates

### 2.3 URL Structure

| Page | URL Pattern | Priority |
|------|-------------|----------|
| Homepage | `/` | High |
| Player Profile | `/players/{letter}/{player_id}.html` | High |
| Player Game Log | `/players/{letter}/{player_id}/gamelog/{year}/` | High |
| Team Page | `/teams/{TEAM}/{year}.html` | High |
| Team Franchise Index | `/teams/{TEAM}/` | Medium |
| Season Overview | `/leagues/NBA_{year}.html` | High |
| Season Stats | `/leagues/NBA_stats_per_game.html` | High |
| Season Standings | `/leagues/NBA_{year}_standings.html` | High |
| Season Schedule | `/leagues/NBA_{year}_games.html` | Medium |
| Game Box Score | `/boxscores/{YYYYMMDD0}{team1}{team2}.html` | Medium |
| Leaders | `/leaders/` | Medium |
| Playoffs | `/playoffs/` | Medium |
| Draft | `/draft/` | Low |
| Awards | `/awards/` | Low |

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Web Framework | FastAPI | ^0.115.0 | Modern, fast Python web framework |
| Database | DuckDB | ^1.1.3 | In-process analytical SQL database |
| ORM/Models | Pydantic | Latest | Data validation and serialization |
| Templating | Jinja2 | ^3.1.4 | HTML template rendering |
| Server | Uvicorn | ^0.32.0 | ASGI server implementation |
| Data Processing | pandas | ^2.2.3 | Data manipulation and ETL |

### 3.2 Frontend

| Component | Technology | Purpose |
|-----------|------------|---------|
| CSS Framework | Tailwind CSS | Utility-first CSS framework |
| Interactions | HTMX | AJAX, server-driven UI updates without heavy JS |
| Data Tables | Tabulator.js | Feature-rich interactive tables |
| Icons | Phosphor Icons | Modern icon library |

### 3.3 Data Sources

| Source | Purpose | Notes |
|--------|---------|-------|
| **nba_api** | Official NBA.com API client for Python | Primary source for recent seasons |
| **basketball-reference CSV exports** | Historical data (1946-2020) | Manual import for historical backfill |
| **Kaggle datasets** | Supplementary historical data | Community-maintained datasets |
| **Daily update scripts** | Automated data refresh | Cron job for daily game updates |

### 3.4 Development Tools

| Tool | Purpose |
|------|---------|
| **uv** or **poetry** | Python dependency management |
| **pytest** | Testing framework |
| **ruff** | Python linting and formatting |

---

## 4. Database Schema

The database uses DuckDB with a star schema optimized for analytical queries.

### 4.1 Core Tables

#### Players (Dimension Table)
```sql
CREATE TABLE players (
    player_id VARCHAR PRIMARY KEY,
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    birth_date DATE,
    birth_place VARCHAR,
    birth_country VARCHAR,
    college VARCHAR,
    draft_year INTEGER,
    draft_round INTEGER,
    draft_pick INTEGER,
    draft_team_id VARCHAR,
    position VARCHAR,
    height_cm INTEGER,
    weight_kg INTEGER,
    shoots VARCHAR(1),
    active BOOLEAN DEFAULT TRUE,
    hall_of_fame BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (draft_team_id) REFERENCES teams(team_id)
);
```

#### Teams (Dimension Table)
```sql
CREATE TABLE teams (
    team_id VARCHAR PRIMARY KEY,
    team_name VARCHAR NOT NULL,
    team_abbrev VARCHAR(3) NOT NULL UNIQUE,
    city VARCHAR,
    state VARCHAR,
    conference VARCHAR(3),  -- 'EAST' or 'WEST'
    division VARCHAR,
    founded_year INTEGER,
    franchise_id VARCHAR,  -- For tracking relocations
    current_abbrev VARCHAR(3)  -- Current abbreviation if team relocated
);
```

#### Seasons (Dimension Table)
```sql
CREATE TABLE seasons (
    season_id VARCHAR PRIMARY KEY,
    year_start INTEGER NOT NULL,
    year_end INTEGER NOT NULL,
    league VARCHAR DEFAULT 'NBA',
    display_name VARCHAR  -- e.g., "2023-24"
);
```

#### Games (Fact Table)
```sql
CREATE TABLE games (
    game_id VARCHAR PRIMARY KEY,
    season_id VARCHAR,
    game_date DATE NOT NULL,
    home_team_id VARCHAR,
    away_team_id VARCHAR,
    home_score INTEGER,
    away_score INTEGER,
    home_q1 INTEGER,
    home_q2 INTEGER,
    home_q3 INTEGER,
    home_q4 INTEGER,
    home_ot INTEGER,
    away_q1 INTEGER,
    away_q2 INTEGER,
    away_q3 INTEGER,
    away_q4 INTEGER,
    away_ot INTEGER,
    is_playoff BOOLEAN DEFAULT FALSE,
    is_overtime BOOLEAN DEFAULT FALSE,
    attendance INTEGER,
    arena VARCHAR,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);
```

#### Player Season Stats (Fact Table)
```sql
CREATE TABLE player_season_stats (
    stat_id BIGINT PRIMARY KEY,
    player_id VARCHAR,
    season_id VARCHAR,
    team_id VARCHAR,
    age INTEGER,
    games_played INTEGER,
    games_started INTEGER,
    minutes_played INTEGER,
    -- Standard Stats
    field_goals INTEGER,
    field_goal_attempts INTEGER,
    fg_pct FLOAT,
    three_pointers INTEGER,
    three_point_attempts INTEGER,
    fg3_pct FLOAT,
    two_pointers INTEGER,
    two_point_attempts INTEGER,
    fg2_pct FLOAT,
    effective_fg_pct FLOAT,
    free_throws INTEGER,
    free_throw_attempts INTEGER,
    ft_pct FLOAT,
    offensive_rebounds INTEGER,
    defensive_rebounds INTEGER,
    total_rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    points INTEGER,
    -- Per Game Stats (can be calculated)
    -- Advanced Stats (populated after basic data validation)
    per FLOAT,
    ts_pct FLOAT,
    usg_pct FLOAT,
    ortg FLOAT,
    drtg FLOAT,
    ws FLOAT,
    ws_per_48 FLOAT,
    bpm FLOAT,
    vorp FLOAT,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
```

#### Player Game Logs (Fact Table)
```sql
CREATE TABLE player_game_logs (
    log_id BIGINT PRIMARY KEY,
    player_id VARCHAR,
    game_id VARCHAR,
    team_id VARCHAR,
    opponent_id VARCHAR,
    is_home BOOLEAN,
    is_win BOOLEAN,
    minutes_played INTEGER,
    field_goals INTEGER,
    field_goal_attempts INTEGER,
    fg_pct FLOAT,
    three_pointers INTEGER,
    three_point_attempts INTEGER,
    fg3_pct FLOAT,
    free_throws INTEGER,
    free_throw_attempts INTEGER,
    ft_pct FLOAT,
    offensive_rebounds INTEGER,
    defensive_rebounds INTEGER,
    total_rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    points INTEGER,
    plus_minus INTEGER,
    -- Calculated stats
    ts_pct FLOAT,
    efg_pct FLOAT,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (opponent_id) REFERENCES teams(team_id)
);
```

#### Team Season Stats (Fact Table)
```sql
CREATE TABLE team_season_stats (
    stat_id BIGINT PRIMARY KEY,
    team_id VARCHAR,
    season_id VARCHAR,
    wins INTEGER,
    losses INTEGER,
    win_pct FLOAT,
    -- Offensive Stats
    games_played INTEGER,
    minutes_played INTEGER,
    points_for INTEGER,
    pts_per_game FLOAT,
    field_goals INTEGER,
    field_goal_attempts INTEGER,
    fg_pct FLOAT,
    three_pointers INTEGER,
    three_point_attempts INTEGER,
    fg3_pct FLOAT,
    free_throws INTEGER,
    free_throw_attempts INTEGER,
    ft_pct FLOAT,
    offensive_rebounds INTEGER,
    defensive_rebounds INTEGER,
    total_rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    -- Defensive Stats
    points_against INTEGER,
    opp_pts_per_game FLOAT,
    opp_field_goals INTEGER,
    opp_field_goal_attempts INTEGER,
    opp_fg_pct FLOAT,
    opp_three_pointers INTEGER,
    opp_three_point_attempts INTEGER,
    opp_fg3_pct FLOAT,
    opp_free_throws INTEGER,
    opp_free_throw_attempts INTEGER,
    opp_ft_pct FLOAT,
    opp_offensive_rebounds INTEGER,
    opp_defensive_rebounds INTEGER,
    opp_total_rebounds INTEGER,
    opp_assists INTEGER,
    opp_steals INTEGER,
    opp_blocks INTEGER,
    opp_turnovers INTEGER,
    opp_personal_fouls INTEGER,
    -- Advanced Stats
    pace FLOAT,
    srs FLOAT,  -- Simple Rating System
    ortg FLOAT,  -- Offensive Rating
    drtg FLOAT,  -- Defensive Rating
    nrtg FLOAT,  -- Net Rating
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
);
```

#### Awards (Fact Table)
```sql
CREATE TABLE awards (
    award_id BIGINT PRIMARY KEY,
    award_name VARCHAR NOT NULL,
    award_type VARCHAR,  -- 'MVP', 'ROY', 'DPOY', 'ALL_NBA', etc.
    season_id VARCHAR,
    player_id VARCHAR,
    team_id VARCHAR,
    rank INTEGER,  -- 1 for winner, 2 for runner-up, etc.
    points_won INTEGER,  -- voting points if applicable
    points_max INTEGER,  -- maximum possible points
    share FLOAT,  -- share of votes
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
);
```

#### Draft Picks (Fact Table)
```sql
CREATE TABLE draft_picks (
    draft_id BIGINT PRIMARY KEY,
    season_id VARCHAR,
    round INTEGER,
    pick_number INTEGER,
    team_id VARCHAR,
    player_id VARCHAR,
    college VARCHAR,
    nationality VARCHAR,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
```

### 4.2 Indexes

```sql
-- Performance indexes for frequently queried columns
CREATE INDEX idx_players_name ON players(last_name, first_name);
CREATE INDEX idx_players_active ON players(active);
CREATE INDEX idx_games_date ON games(game_date);
CREATE INDEX idx_games_season ON games(season_id);
CREATE INDEX idx_player_season_stats_player ON player_season_stats(player_id);
CREATE INDEX idx_player_season_stats_season ON player_season_stats(season_id);
CREATE INDEX idx_player_game_logs_player ON player_game_logs(player_id);
CREATE INDEX idx_player_game_logs_game ON player_game_logs(game_id);
CREATE INDEX idx_team_season_stats_team ON team_season_stats(team_id);
CREATE INDEX idx_team_season_stats_season ON team_season_stats(season_id);
```

---

## 5. Feature Requirements

### 5.1 Version 1.0 - Core Player Features

#### Player Profile Pages
**Priority: CRITICAL**

- [ ] Player bio information display:
  - Name, position, height, weight
  - Birth date and place
  - College
  - Draft year, round, pick, team
  - Shooting hand
  - Hall of Fame status
  
- [ ] Career statistics summary table
  - Aggregate career totals
  - Career per-game averages
  
- [ ] Season-by-season statistics table with views:
  - Per Game stats
  - Total stats
  - Per 36 Minutes
  - Per 100 Possessions
  - Advanced stats (PER, TS%, USG%, ORtg, DRtg, WS, BPM, VORP)
  
- [ ] Season selector dropdown for quick navigation
- [ ] Team history (all teams played for by season)

#### Player Game Logs
**Priority: CRITICAL**

- [ ] Individual game statistics by season
- [ ] Sortable columns
- [ ] Pagination (50/100/200/All rows per page)
- [ ] CSV export functionality
- [ ] Basic filtering (home/away, wins/losses)

#### Search & Navigation
**Priority: CRITICAL**

- [ ] Global player search (fuzzy matching)
- [ ] Player index page (alphabetical by last name)
- [ ] Breadcrumb navigation

### 5.2 Version 2.0 - Team Features

#### Team Season Pages
**Priority: HIGH**

- [ ] Season roster with player statistics
- [ ] Team season totals and rankings
- [ ] Schedule and results table
- [ ] Win/loss margin visualization
- [ ] Division/Conference standings

#### Team Franchise Pages
**Priority: MEDIUM**

- [ ] Franchise overview and history
- [ ] All-time roster
- [ ] Franchise leaders (career records)
- [ ] Season-by-season results
- [ ] Draft history

### 5.3 Version 3.0 - League & Season Features

#### Season Overview Pages
**Priority: HIGH**

- [ ] Standings (conference and division)
- [ ] League leaders in major categories
- [ ] Rookie statistics
- [ ] Season schedule with scores

#### League Statistics Pages
**Priority: MEDIUM**

- [ ] League-wide statistical tables
- [ ] Historical league averages
- [ ] Statistical trends over time

### 5.4 Version 4.0 - Game & Advanced Features

#### Game Box Scores
**Priority: MEDIUM**

- [ ] Individual game pages
- [ ] Player statistics for both teams
- [ ] Team totals and comparison
- [ ] Quarter-by-quarter scoring
- [ ] Basic and advanced box score views

#### Leaders & Records
**Priority: MEDIUM**

- [ ] Season leaders by category
- [ ] Career leaders
- [ ] Single game records
- [ ] Active player leaders

### 5.5 Version 5.0 - Historical & Supplementary

#### Playoffs
**Priority: LOW**

- [ ] Playoff brackets by year
- [ ] Series summaries
- [ ] Historical champions listing

#### Draft
**Priority: LOW**

- [ ] Draft history by year
- [ ] Player draft position tracking

#### Awards
**Priority: LOW**

- [ ] Award index (MVP, All-NBA, ROY, DPOY, etc.)
- [ ] Historical award winners by year
- [ ] Voting results where available

### 5.6 Future Enhancements (Post v5.0)

- [ ] Data visualization charts (shot charts, team trends)
- [ ] Player comparison tool
- [ ] Custom SQL query interface
- [ ] Fantasy basketball projections
- [ ] Playoff simulator

---

## 6. UI/UX Design Guidelines

### 6.1 Layout Structure

```
+----------------------------------+
|           Header                 |
|  Logo | Nav | Search | About     |
+----------------------------------+
|                                  |
|  Breadcrumbs                     |
|                                  |
+----------------------------------+
| Sidebar |    Main Content        |
|         |                        |
| Quick   |    Statistics Tables   |
| Links   |                        |
|         |    Tab Views           |
|         |                        |
+----------------------------------+
|           Footer                 |
+----------------------------------+
```

### 6.2 Header
- Fixed position at top
- Site logo on left
- Navigation links: Players, Teams, Seasons, Games
- Global search bar (player/team search)
- Mobile hamburger menu

### 6.3 Sidebar (Detail Pages)
- Quick navigation within page
- Related links
- Season selector dropdown
- Jump to section links

### 6.4 Tables

**Tabulator.js Configuration:**
- Sortable columns (click headers)
- Filterable columns
- Pagination controls
- Horizontal scrolling for wide tables
- Sticky/frozen first column (player names)
- Alternating row colors
- Row highlight on hover
- CSV export button
- Column visibility toggles

**Responsive Design:**
- Mobile: Horizontal scroll for tables
- Tablet: Condensed view with column selection
- Desktop: Full table view

### 6.5 Color Scheme

**Primary Colors:**
- Primary Blue: `#17408B` (NBA blue)
- Secondary Red: `#C9082A` (NBA red)
- Background: `#FFFFFF`
- Alternate Background: `#F8F9FA`

**Table Colors:**
- Header Background: `#17408B`
- Header Text: `#FFFFFF`
- Row Hover: `#E3F2FD`
- Border: `#DEE2E6`
- Even Rows: `#F8F9FA`

### 6.6 Typography
- Primary Font: System font stack
- Headers: 600 weight
- Body: 400 weight
- Table Data: Monospace for numbers

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goals:** Set up project infrastructure and initial data layer

- [ ] Set up project structure with FastAPI + DuckDB
- [ ] Configure Tailwind CSS build pipeline
- [ ] Set up HTMX and Tabulator.js
- [ ] Create base HTML templates (base.html, navigation, footer)
- [ ] Create initial database schema
- [ ] Write database connection management module
- [ ] Set up ETL pipeline structure
- [ ] Create data validation utilities

**Deliverables:**
- Working development server
- Database schema created
- Base templates ready
- ETL framework in place

### Phase 2: Data Ingestion (Weeks 3-5)

**Goals:** Populate database with historical data

- [ ] Build NBA API client wrapper
- [ ] Create historical data import scripts
- [ ] Import team data (all franchises)
- [ ] Import player data (1946-present)
- [ ] Import game data (1946-present)
- [ ] Import player season stats (1946-present)
- [ ] Import player game logs (priority: recent seasons first)
- [ ] Data validation and quality checks
- [ ] Build data update utilities

**Deliverables:**
- Fully populated database
- Data quality reports
- ETL scripts documented
- Data update procedures

### Phase 3: Player Features v1.0 (Weeks 6-8)

**Goals:** Complete player profile functionality

- [ ] Build player profile API endpoints
- [ ] Create player profile template
- [ ] Implement career stats tables
- [ ] Implement season-by-season stats tables
- [ ] Add statistical view switching (tabs)
- [ ] Build player game log pages
- [ ] Implement game log filtering
- [ ] Add CSV export to tables
- [ ] Create player search functionality
- [ ] Build player index page

**Deliverables:**
- Player profiles fully functional
- Game logs working
- Search implemented
- CSV export enabled

### Phase 4: Team Features v2.0 (Weeks 9-11)

**Goals:** Complete team functionality

- [ ] Build team season page API endpoints
- [ ] Create team season templates
- [ ] Implement roster tables
- [ ] Build team schedule/results pages
- [ ] Create standings pages
- [ ] Build franchise history pages
- [ ] Implement team statistics views

**Deliverables:**
- Team pages fully functional
- Standings working
- Franchise history accessible

### Phase 5: League Features v3.0 (Weeks 12-13)

**Goals:** Complete season/league functionality

- [ ] Build season overview pages
- [ ] Create league statistics tables
- [ ] Implement league leaders pages
- [ ] Build season schedule pages
- [ ] Add historical league averages

**Deliverables:**
- Season pages working
- League stats accessible
- Leaders tracked

### Phase 6: Game & Advanced v4.0 (Weeks 14-15)

**Goals:** Complete game features

- [ ] Build game box score pages
- [ ] Create play-by-play display (if available)
- [ ] Implement advanced statistics calculations
- [ ] Build leaders and records pages

**Deliverables:**
- Box scores working
- Advanced stats calculated
- Records tracked

### Phase 7: Historical Data v5.0 (Weeks 16-17)

**Goals:** Complete historical features

- [ ] Build playoff bracket pages
- [ ] Create draft history pages
- [ ] Implement awards tracking
- [ ] Backfill any missing historical data

**Deliverables:**
- Playoffs accessible
- Draft history available
- Awards tracked

### Phase 8: Automation & Polish (Week 18+)

**Goals:** Set up automation and finalize

- [ ] Implement daily data update scripts
- [ ] Add data visualization charts
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation

**Deliverables:**
- Automated updates working
- Charts implemented
- Performance optimized
- Documentation complete

---

## 8. Data Strategy

### 8.1 Initial Data Ingestion (1946-Present)

**Phase 1: Teams and Players**
- Import all NBA franchises and team history
- Import all players (career totals and bios)

**Phase 2: Games**
- Import all games (1946-present)
- Import quarterly scores
- Import game metadata (attendance, arena)

**Phase 3: Player Statistics**
- Import player season stats (1946-present)
- Import player game logs (prioritize recent seasons)
- Calculate per-game averages

**Phase 4: Advanced Statistics**
- Calculate advanced metrics (PER, WS, BPM, VORP)
- Validate calculations against known values

### 8.2 Daily Update Strategy

**Update Frequency:** Daily at 6:00 AM (after last night's games)

**Update Process:**
```python
# Daily update script (cron job)
1. Check for new games from last 24 hours
2. Insert new games into database
3. Update player_game_logs with new entries
4. Recalculate player_season_stats aggregates
5. Recalculate team_season_stats aggregates
6. Update standings
7. Update league averages
8. Log update results
```

**Data Sources:**
- **Recent seasons (2020-present):** NBA API
- **Historical backfill:** CSV exports, Kaggle datasets

### 8.3 Data Validation

- Cross-reference totals with official NBA statistics
- Validate player career totals sum correctly
- Check game scores match box score totals
- Verify advanced stat calculations

---

## 9. Project Structure

```
hoopsdb/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry
│   ├── config.py                # Configuration settings
│   ├── database.py              # DuckDB connection management
│   ├── models.py                # Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── players.py           # Player API endpoints
│   │   ├── teams.py             # Team API endpoints
│   │   ├── seasons.py           # Season API endpoints
│   │   ├── games.py             # Game API endpoints
│   │   ├── search.py            # Search API endpoints
│   │   └── boxscores.py         # Box score API endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── player_service.py    # Player business logic
│   │   ├── team_service.py      # Team business logic
│   │   ├── stats_service.py     # Statistics calculations
│   │   └── search_service.py    # Search functionality
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── partials/            # Reusable template components
│       │   ├── navigation.html
│       │   ├── footer.html
│       │   ├── search_bar.html
│       │   └── stats_table.html
│       ├── player/
│       │   ├── profile.html
│       │   ├── gamelog.html
│       │   └── index.html
│       ├── team/
│       │   ├── season.html
│       │   ├── franchise.html
│       │   └── index.html
│       ├── season/
│       │   ├── overview.html
│       │   ├── standings.html
│       │   └── leaders.html
│       └── game/
│           └── boxscore.html
├── data/
│   ├── raw/                     # Raw data files (CSV, Parquet)
│   ├── processed/               # Processed/transformed data
│   ├── import/                  # Data import scripts
│   │   ├── __init__.py
│   │   ├── init_db.py           # Database initialization
│   │   ├── import_teams.py
│   │   ├── import_players.py
│   │   ├── import_games.py
│   │   ├── import_stats.py
│   │   ├── calculate_advanced.py
│   │   └── update_daily.py      # Daily update script
│   └── hoopsdb.duckdb           # Main database file
├── static/
│   ├── css/
│   │   └── main.css             # Tailwind compiled or custom
│   ├── js/
│   │   ├── tables.js            # Tabulator.js configuration
│   │   └── search.js            # Search functionality
│   └── images/
│       └── logo.png
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_services.py
│   └── test_data_import.py
├── scripts/
│   ├── setup.sh                 # Setup script
│   └── cron_setup.sh            # Cron job setup
├── requirements.txt
├── pyproject.toml               # Modern Python packaging
├── .env.example                 # Environment variables template
├── .gitignore
└── README.md
```

---

## 10. Appendix

### 10.1 NBA Team Abbreviations Reference

| Abbr | Team Name | Conference | Division |
|------|-----------|------------|----------|
| ATL | Atlanta Hawks | East | Southeast |
| BOS | Boston Celtics | East | Atlantic |
| BRK | Brooklyn Nets | East | Atlantic |
| CHO | Charlotte Hornets | East | Southeast |
| CHI | Chicago Bulls | East | Central |
| CLE | Cleveland Cavaliers | East | Central |
| DAL | Dallas Mavericks | West | Southwest |
| DEN | Denver Nuggets | West | Northwest |
| DET | Detroit Pistons | East | Central |
| GSW | Golden State Warriors | West | Pacific |
| HOU | Houston Rockets | West | Southwest |
| IND | Indiana Pacers | East | Central |
| LAC | LA Clippers | West | Pacific |
| LAL | Los Angeles Lakers | West | Pacific |
| MEM | Memphis Grizzlies | West | Southwest |
| MIA | Miami Heat | East | Southeast |
| MIL | Milwaukee Bucks | East | Central |
| MIN | Minnesota Timberwolves | West | Northwest |
| NOP | New Orleans Pelicans | West | Southwest |
| NYK | New York Knicks | East | Atlantic |
| OKC | Oklahoma City Thunder | West | Northwest |
| ORL | Orlando Magic | East | Southeast |
| PHI | Philadelphia 76ers | East | Atlantic |
| PHO | Phoenix Suns | West | Pacific |
| POR | Portland Trail Blazers | West | Northwest |
| SAC | Sacramento Kings | West | Pacific |
| SAS | San Antonio Spurs | West | Southwest |
| TOR | Toronto Raptors | East | Atlantic |
| UTA | Utah Jazz | West | Northwest |
| WAS | Washington Wizards | East | Southeast |

### 10.2 Open Source Libraries Summary

| Library | License | Purpose |
|---------|---------|---------|
| FastAPI | MIT | Web framework |
| DuckDB | MIT | Analytical database |
| HTMX | BSD-2 | Frontend interactivity |
| Tabulator.js | MIT | Data tables |
| Tailwind CSS | MIT | CSS framework |
| Phosphor Icons | MIT | Icon library |
| Pydantic | MIT | Data validation |
| Jinja2 | BSD | Templating |
| Uvicorn | BSD | ASGI server |
| pandas | BSD | Data manipulation |
| nba_api | MIT | NBA data API |
| pytest | MIT | Testing |
| ruff | MIT | Linting |

**Total Stack Cost:** $0 (All MIT/BSD licensed)

### 10.3 Key Abbreviations

| Abbreviation | Full Name |
|--------------|-----------|
| FGA | Field Goal Attempts |
| FG% | Field Goal Percentage |
| 3P | Three Pointers Made |
| 3PA | Three Point Attempts |
| 3P% | Three Point Percentage |
| FT | Free Throws Made |
| FTA | Free Throw Attempts |
| FT% | Free Throw Percentage |
| ORB | Offensive Rebounds |
| DRB | Defensive Rebounds |
| TRB | Total Rebounds |
| AST | Assists |
| STL | Steals |
| BLK | Blocks |
| TOV | Turnovers |
| PF | Personal Fouls |
| PTS | Points |
| PER | Player Efficiency Rating |
| TS% | True Shooting Percentage |
| USG% | Usage Percentage |
| ORtg | Offensive Rating |
| DRtg | Defensive Rating |
| WS | Win Shares |
| BPM | Box Plus/Minus |
| VORP | Value Over Replacement Player |
| SRS | Simple Rating System |
| EFG% | Effective Field Goal Percentage |

### 10.4 Success Metrics

- [ ] All basketball-reference.com core pages replicable locally
- [ ] Page load time < 2 seconds for player/team pages
- [ ] Complete NBA historical data (1946-present) imported
- [ ] Daily data updates automated
- [ ] CSV export works on all data tables
- [ ] Search returns results in < 500ms
- [ ] 100% open-source stack (zero proprietary dependencies)
- [ ] All advanced statistics validated against official sources


**END OF DOCUMENT**
