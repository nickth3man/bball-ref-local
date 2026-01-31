# NBA Statistics Bible: Complete Formula Reference

**Version:** 1.0  
**Last Updated:** 2026-01-31  
**Sources:** Basketball-Reference.com, NBA.com, ESPN Hollinger Analytics

---

## Table of Contents

1. [Foundational Concepts](#1-foundational-concepts)
2. [Box Score Statistics](#2-box-score-statistics)
3. [Shooting Percentages](#3-shooting-percentages)
4. [Possession Calculations](#4-possession-calculations)
5. [Rate Statistics](#5-rate-statistics)
6. [Advanced Statistics](#6-advanced-statistics)
7. [Stat Formatting by Context](#7-stat-formatting-by-context)
8. [Calculation Examples](#8-calculation-examples)

---

## 1. Foundational Concepts

### 1.1 The Possession

A **possession** is the fundamental unit of basketball analytics. A possession ends when:
- A field goal is attempted (without offensive rebound)
- A turnover occurs
- Free throws are attempted (that end the possession)

Offensive rebounds **do NOT** start a new possession—they extend the existing one.

### 1.2 The 0.44 Coefficient

The coefficient **0.44** represents the empirical finding that approximately 44% of free throw attempts actually conclude a possession. The remaining 56% occur in:
- Technical fouls
- "And-one" opportunities
- Flagrant fouls
- Multiple free throws within the same possession

This coefficient was derived from analysis of thousands of NBA play-by-play possessions.

---

## 2. Box Score Statistics

### 2.1 Traditional Counting Stats

| Stat | Abbreviation | Definition |
|------|--------------|------------|
| Points | PTS | Total points scored from all sources |
| Field Goals Made | FGM / FG | Two-point and three-point shots made |
| Field Goals Attempted | FGA | Two-point and three-point shots attempted |
| Three-Pointers Made | 3PM / 3P | Three-point shots made |
| Three-Pointers Attempted | 3PA | Three-point shots attempted |
| Two-Pointers Made | 2PM | Two-point shots made (FGM - 3PM) |
| Two-Pointers Attempted | 2PA | Two-point shots attempted (FGA - 3PA) |
| Free Throws Made | FTM / FT | Free throws made |
| Free Throws Attempted | FTA | Free throws attempted |
| Offensive Rebounds | ORB / OREB | Rebounds on offensive end |
| Defensive Rebounds | DRB / DREB | Rebounds on defensive end |
| Total Rebounds | TRB / REB | Total rebounds (ORB + DRB) |
| Assists | AST | Passes leading directly to made baskets |
| Steals | STL | Defensive takeaways |
| Blocks | BLK | Defensive deflections preventing scores |
| Turnovers | TOV / TO | Loss of possession to opponent |
| Personal Fouls | PF | Rule infractions (excluding technicals) |
| Minutes Played | MP / MIN | Time on court (available since 1951-52) |
| Plus/Minus | +/- | Team point differential while on court |

### 2.2 Derived Counting Stats

```
2PM = FGM - 3PM
2PA = FGA - 3PA
TRB = ORB + DRB
```

---

## 3. Shooting Percentages

### 3.1 Standard Percentages

```
FG% = FGM / FGA
3P% = 3PM / 3PA
2P% = 2PM / 2PA
FT% = FTM / FTA
```

### 3.2 Effective Field Goal Percentage (eFG%)

Adjusts FG% to account for the extra value of three-pointers.

```
eFG% = (FGM + 0.5 * 3PM) / FGA
```

**Why 0.5?** Each 3-pointer is worth 1.5 times a 2-pointer, so the additional 0.5 accounts for the extra point.

### 3.3 True Shooting Percentage (TS%)

Measures overall scoring efficiency across all shot types.

```
TS% = PTS / (2 * (FGA + 0.44 * FTA))
```

Or using True Shooting Attempts (TSA):
```
TSA = FGA + 0.44 * FTA
TS% = PTS / (2 * TSA)
```

**Interpretation:**
- League average: ~56-58%
- Elite: 60%+
- Poor: <50%

---

## 4. Possession Calculations

### 4.1 Team Possessions

```
Possessions = FGA + 0.44 * FTA + TOV - ORB
```

Alternative (both teams should have same possessions in a game):
```
Possessions = 0.5 * ((Team_FGA + 0.44 * Team_FTA - Team_ORB + Team_TOV) + 
                      (Opp_FGA + 0.44 * Opp_FTA - Opp_ORB + Opp_TOV))
```

### 4.2 Pace

Possessions per 48 minutes (normalizes for playing time and overtime).

```
Pace = 48 * ((Team_Poss + Opp_Poss) / (2 * (Team_MP / 5)))
```

Where:
- Team_MP = Total team minutes played (typically 240 for regulation: 5 players × 48 minutes)

### 4.3 Player Possessions

Individual possessions scaled by playing time:

```
Player_Poss% = (FGA + 0.44 * FTA + TOV) * (Team_MP / 5) / (MP * Team_Poss)
```

---

## 5. Rate Statistics

### 5.1 Per 36 Minutes

Standardizes counting stats to 36 minutes (approximate starter minutes).

```
Per36 = (Stat / MP) * 36
```

### 5.2 Per 100 Possessions

Pace-adjusted rate (allows comparison across different team speeds).

```
Per100 = (Stat / Possessions) * 100
```

### 5.3 Usage Percentage (USG%)

Percentage of team plays used by a player while on court.

```
USG% = 100 * ((FGA + 0.44 * FTA + TOV) * (Team_MP / 5)) / 
       (MP * (Team_FGA + 0.44 * Team_FTA + Team_TOV))
```

**Interpretation:**
- 25-30%: Primary option/star
- 20-25%: Secondary option
- 15-20%: Role player
- <15%: Limited role

### 5.4 Assist Percentage (AST%)

```
AST% = 100 * AST / (((MP / (Team_MP / 5)) * Team_FGM) - FGM)
```

### 5.5 Rebound Percentages

**Offensive Rebound %:**
```
ORB% = 100 * (ORB * (Team_MP / 5)) / (MP * (Team_ORB + Opp_DRB))
```

**Defensive Rebound %:**
```
DRB% = 100 * (DRB * (Team_MP / 5)) / (MP * (Team_DRB + Opp_ORB))
```

**Total Rebound %:**
```
TRB% = 100 * (TRB * (Team_MP / 5)) / (MP * (Team_TRB + Opp_TRB))
```

### 5.6 Steal Percentage (STL%)

```
STL% = 100 * (STL * (Team_MP / 5)) / (MP * Opp_Possessions)
```

### 5.7 Block Percentage (BLK%)

```
BLK% = 100 * (BLK * (Team_MP / 5)) / (MP * (Opp_FGA - Opp_3PA))
```

Note: Excludes opponent 3-point attempts (blocks on 3s are rare).

### 5.8 Turnover Percentage (TOV%)

```
TOV% = 100 * TOV / (FGA + 0.44 * FTA + TOV)
```

---

## 6. Advanced Statistics

### 6.1 Player Efficiency Rating (PER)

**Unadjusted PER (uPER):**

```
uPER = (1/MP) * [
    3P
    + (2/3) * AST
    + (2 - factor * (team_AST/team_FG)) * FG
    + FT * 0.5 * (1 + (1 - (team_AST/team_FG)) + (2/3)*(team_AST/team_FG))
    - VOP * TOV
    - VOP * DRB% * (FGA - FG)
    - VOP * 0.44 * (0.44 + 0.56 * DRB%) * (FTA - FT)
    + VOP * (1 - DRB%) * (TRB - ORB)
    + VOP * DRB% * ORB
    + VOP * STL
    + VOP * DRB% * BLK
    - PF * ((lg_FT/lg_PF) - 0.44 * (lg_FTA/lg_PF) * VOP)
]
```

**Where:**
```
factor = (2/3) - (0.5 * (lg_AST/lg_FG)) / (2 * (lg_FG/lg_FT))
VOP = lg_PTS / (lg_FGA - lg_ORB + lg_TOV + 0.44 * lg_FTA)
DRB% = (lg_TRB - lg_ORB) / lg_TRB
```

**Pace Adjustment:**
```
pace_adj = lg_Pace / team_Pace
aPER = uPER * pace_adj
```

**Final PER (normalized to 15.0):**
```
PER = aPER * (15 / lg_aPER)
```

**Interpretation:**
- 30.0+: MVP level
- 25.0-29.9: All-NBA level
- 20.0-24.9: All-Star level
- 15.0-19.9: Above average
- 10.0-14.9: Below average
- <10.0: Poor

### 6.2 Box Plus/Minus (BPM)

**Raw BPM Formula (with regression coefficients):**

```
Raw BPM = a*ReMPG + b*ORB% + c*DRB% + d*STL% + e*BLK% + f*AST%
          - g*USG%*TOV% + h*USG%*(1-TOV%)*[2*(TS%-TmTS%) + i*AST% + j*(3PAr-Lg3PAr) - k]
          + l*sqrt(AST%*TRB%)
```

**Coefficients:**

| Coeff | Term | Value |
|-------|------|-------|
| a | Regressed MPG | 0.096255 |
| b | ORB% | 0.079971 |
| c | DRB% | 0.038671 |
| d | STL% | 0.107788 |
| e | BLK% | 0.110657 |
| f | AST% | -0.053849 |
| g | USG%×TOV% | 0.039891 |
| h | Scaling | 0.500000 |
| i | AST% adj | 0.034702 |
| j | 3PAr adj | 0.213705 |
| k | Threshold | 0.213485 |
| l | sqrt(AST%×TRB%) | 0.725930 |

**Team Adjustment:**
```
Team_Adj = [Team_Rating * 1.20 - sum(Player_%Min * Player_RawBPM)] / 5
BPM = Raw_BPM + Team_Adj
```

**Interpretation:**
- +8.0+: MVP candidate
- +6.0 to +8.0: All-NBA candidate
- +4.0 to +6.0: All-Star
- +2.0 to +4.0: Good starter
- 0.0 to +2.0: Rotation player
- -2.0 to 0.0: Below average
- <-2.0: Replacement level

### 6.3 Offensive Box Plus/Minus (OBPM)

**OBPM Coefficients:**

| Coeff | Term | Value |
|-------|------|-------|
| a | Regressed MPG | 0.064448 |
| b | ORB% | 0.211125 |
| c | DRB% | -0.107545 |
| d | STL% | -0.080357 |
| e | BLK% | -0.040223 |
| f | AST% | 0.267875 |
| g | USG%×TOV% | 0.133382 |
| h | Scaling | 0.500000 |
| i | AST% adj | 0.125766 |
| j | 3PAr adj | 0.221697 |
| k | Threshold | -0.181891 |
| l | sqrt(AST%×TRB%) | 0.239862 |

### 6.4 Defensive Box Plus/Minus (DBPM)

```
DBPM = BPM - OBPM
```

Note: DBPM is less reliable than OBPM because many defensive contributions aren't captured in box scores.

### 6.5 Value Over Replacement Player (VORP)

```
VORP = (BPM - (-2.0)) * (%Min) * (Team_Games / 82)
```

Where:
- -2.0 = Replacement level BPM
- %Min = Player's percentage of team minutes
- Team_Games = Games played by team

**Interpretation:**
- 0: Replacement level
- 5: Solid contributor
- 10-15: All-Star level
- 20+: MVP level

### 6.6 Win Shares (WS)

#### 6.6.1 Offensive Win Shares (OWS)

```
Points_Produced = (FGA + 0.44*FTA + TOV) * (Offensive_Rating / 100)
Marginal_Offense = Points_Produced - 0.92 * (lg_Pts_per_Poss) * Offensive_Possessions
Marginal_Pts_per_Win = 0.32 * lg_PPG * (Team_Pace / lg_Pace)
OWS = Marginal_Offense / Marginal_Pts_per_Win
```

#### 6.6.2 Defensive Win Shares (DWS)

Based on Defensive Rating and team defensive efficiency:
```
Marginal_Defense = Defensive_Possessions * (lg_Pts_per_Poss - Player_Defensive_Rating/100)
DWS = Marginal_Defense / Marginal_Pts_per_Win
```

#### 6.6.3 Total Win Shares

```
WS = OWS + DWS
```

#### 6.6.4 Win Shares Per 48 Minutes (WS/48)

```
WS/48 = WS * (48 / MP)
```

**Interpretation:**
- 0.200+: MVP candidate
- 0.150-0.199: All-Star
- 0.100-0.149: Starter
- 0.070-0.099: Role player
- 0.000-0.069: Fringe player

### 6.7 Offensive Rating (ORtg)

Points produced per 100 possessions.

```
ORtg = 100 * (Points_Produced / Total_Possessions)
```

### 6.8 Defensive Rating (DRtg)

Points allowed per 100 possessions.

```
DRtg = Team_DRtg + 0.2 * (100 * D_Pts_per_ScPoss * (1 - Stop%) - Team_DRtg)
```

Where Stop% involves STL, BLK, DRB, opponent FG% and ORB%.

### 6.9 Simple Rating System (SRS)

Team strength accounting for point differential and strength of schedule.

```
Margin = PPG_For - PPG_Against
SOS = Average Margin of Opponents
SRS = Margin + SOS
```

---

## 7. Stat Formatting by Context

### 7.1 Single Game Box Score

**Display Format:**
- Integer counting stats (no decimals)
- Percentages: 0-1 scale or 0-100% (3 decimal precision internally)
- Minutes: MM:SS or decimal (e.g., 35.5 = 35 min 30 sec)
- Plus/Minus: Signed integer (+/-)

**Example:**
```
Player: 35 MIN, 12 PTS, 5-10 FG, 2-4 3P, 0-0 FT, 3 REB, 4 AST, 1 STL, 0 BLK, 2 TO, +7
```

### 7.2 Season Totals

**Display Format:**
- Counting stats: Integer totals
- Percentages: 3 decimal places (e.g., .456)
- Per game averages: 1 decimal place
- Advanced stats: 1-2 decimal places depending on scale

**Example:**
```
Totals: 82 G, 2460 MIN, 1640 PTS, 620-1240 FG (.500), 120-320 3P (.375)
```

### 7.3 Season Per Game

**Calculation:**
```
Stat_Per_Game = Total_Stat / Games_Played
```

**Display:** 1 decimal place for most stats

**Example:**
```
Per Game: 30.0 MPG, 20.0 PPG, 8.0 RPG, 5.0 APG
```

### 7.4 Career Totals

Sum across all seasons:
```
Career_Stat = sum(Season_Stat) for all seasons
```

### 7.5 Career Per Game

```
Career_Per_Game = Career_Total / Career_Games
```

### 7.6 Rate Normalization

**Per 36 Minutes:**
```
Per36 = (Stat / Minutes) * 36
```

**Per 100 Possessions:**
```
Per100 = (Stat / Possessions) * 100
```

### 7.7 Percentage Display Conventions

| Stat | Internal Storage | Display Format |
|------|-----------------|----------------|
| FG%, 3P%, FT% | Decimal (0-1) | 3 decimals (.456) or % (45.6%) |
| TS%, eFG% | Decimal (0-1) | 3 decimals (.589) |
| Rate % (USG%, AST%, etc.) | Decimal (0-100) | 1 decimal (25.3%) |
| PER | Decimal | 1 decimal (24.5) |
| BPM | Decimal | 1 decimal (+4.2) |
| VORP | Decimal | 1 decimal (3.5) |
| WS | Decimal | 1 decimal (8.5) |
| WS/48 | Decimal | 3 decimals (.156) |

---

## 8. Calculation Examples

### 8.1 True Shooting Percentage Example

**Player Stats:**
- PTS: 30
- FGA: 20
- FTA: 10

**Calculation:**
```
TS% = 30 / (2 * (20 + 0.44 * 10))
TS% = 30 / (2 * (20 + 4.4))
TS% = 30 / (2 * 24.4)
TS% = 30 / 48.8
TS% = 0.615 (61.5%)
```

### 8.2 Effective FG% Example

**Player Stats:**
- FGM: 8
- 3PM: 3
- FGA: 15

**Calculation:**
```
eFG% = (8 + 0.5 * 3) / 15
eFG% = (8 + 1.5) / 15
eFG% = 9.5 / 15
eFG% = 0.633 (63.3%)
```

### 8.3 Usage Rate Example

**Player Stats:**
- FGA: 18
- FTA: 8
- TOV: 3
- MP: 36

**Team Stats:**
- Team_FGA: 90
- Team_FTA: 30
- Team_TOV: 15
- Team_MP: 240 (5 players × 48 min)

**Calculation:**
```
USG% = 100 * ((18 + 0.44 * 8 + 3) * (240/5)) / (36 * (90 + 0.44 * 30 + 15))
USG% = 100 * ((18 + 3.52 + 3) * 48) / (36 * (90 + 13.2 + 15))
USG% = 100 * (24.52 * 48) / (36 * 118.2)
USG% = 100 * 1176.96 / 4255.2
USG% = 27.7%
```

### 8.4 PER Example (Simplified)

Given the complexity of full PER calculation, here's a simplified conceptual walkthrough:

1. Calculate uPER per minute from box score stats
2. Multiply by pace adjustment (lg_Pace / team_Pace)
3. Multiply by normalization factor (15 / lg_aPER)
4. Result: PER normalized to 15.0 = league average

### 8.5 BPM Example (Simplified)

**Player Stats:**
- ReMPG (regressed minutes): 0.75
- ORB%: 3.5
- DRB%: 15.2
- STL%: 1.8
- BLK%: 2.1
- AST%: 22.4
- USG%: 28.0
- TOV%: 12.0
- TS%: 0.58
- TmTS%: 0.56
- 3PAr: 0.35
- Lg3PAr: 0.36
- TRB%: 9.4

**Calculation:**
```
Raw BPM = 0.096255*0.75 + 0.079971*3.5 + 0.038671*15.2 + 
          0.107788*1.8 + 0.110657*2.1 + (-0.053849)*22.4 -
          0.039891*28.0*12.0 + 0.5*28.0*(1-0.12)*[2*(0.58-0.56) + 
          0.034702*22.4 + 0.213705*(0.35-0.36) - 0.213485] +
          0.725930*sqrt(22.4*9.4)

(Detailed calculation steps would follow...)
```

---

## References

1. **Basketball-Reference Glossary:** https://www.basketball-reference.com/about/glossary.html
2. **Basketball-Reference PER:** https://www.basketball-reference.com/about/per.html
3. **Basketball-Reference Win Shares:** https://www.basketball-reference.com/about/ws.html
4. **Basketball-Reference BPM:** https://www.basketball-reference.com/about/bpm2.html
5. **Basketball-Reference Ratings:** https://www.basketball-reference.com/about/ratings.html
6. **NBA.com Stats Glossary:** https://www.nba.com/stats/help/glossary
7. **Hollinger's PER:** ESPN NBA Analytics
8. **Dean Oliver's Basketball on Paper:** Possession-based analytics foundation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-31 | Initial comprehensive bible with all formulas |

---

## Notes for Implementation

### Database Column Naming Conventions

| Stat | Recommended Column Name |
|------|------------------------|
| Field Goals Made | fg_made / field_goals |
| Field Goals Attempted | fg_attempted / field_goal_attempts |
| Field Goal % | fg_pct |
| 3-Pointers Made | fg3_made / three_pointers |
| 3-Pointers Attempted | fg3_attempted / three_point_attempts |
| 3-Point % | fg3_pct |
| Free Throws Made | ft_made / free_throws |
| Free Throws Attempted | ft_attempted / free_throw_attempts |
| Free Throw % | ft_pct |
| Offensive Rebounds | reb_offensive / offensive_rebounds |
| Defensive Rebounds | reb_defensive / defensive_rebounds |
| Total Rebounds | reb_total / total_rebounds |
| Assists | assists |
| Steals | steals |
| Blocks | blocks |
| Turnovers | turnovers |
| Personal Fouls | personal_fouls / fouls |
| Points | points |
| Minutes Played | minutes_played |
| Plus/Minus | plus_minus |
| True Shooting % | ts_pct |
| Effective FG% | efg_pct |
| Usage % | usg_pct |
| Assist % | ast_pct |
| Rebound % | reb_pct |
| Offensive Rebound % | orb_pct |
| Defensive Rebound % | drb_pct |
| Steal % | stl_pct |
| Block % | blk_pct |
| Turnover % | tov_pct |
| Player Efficiency Rating | per |
| Box Plus/Minus | bpm |
| Offensive BPM | obpm |
| Defensive BPM | dbpm |
| Value Over Replacement | vorp |
| Win Shares | ws |
| Win Shares/48 | ws_per_48 |
| Offensive Win Shares | ows |
| Defensive Win Shares | dws |
| Offensive Rating | ortg |
| Defensive Rating | drtg |
| Pace | pace |
| Simple Rating System | srs |

### Data Types

- Counting stats: INTEGER
- Percentages (0-1): FLOAT (store at least 3 decimal precision)
- Rate percentages (0-100): FLOAT
- Advanced stats (PER, BPM, etc.): FLOAT
- Minutes: FLOAT (allows for seconds as decimal)

### Validation Rules

```
FG%: 0 <= fg_pct <= 1
3P%: 0 <= fg3_pct <= 1
FT%: 0 <= ft_pct <= 1
eFG%: 0 <= efg_pct <= 1.5 (can exceed 1 due to 3-point weighting)
TS%: 0 <= ts_pct (no upper bound theoretically, practically < 1.5)
USG%: 0 <= usg_pct <= 100
PER: Typically -5 to 35 (no strict bounds)
BPM: Typically -10 to +10
WS: 0 <= ws (no upper bound)
```
