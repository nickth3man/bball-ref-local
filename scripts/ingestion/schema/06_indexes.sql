-- ============================================================================
-- 06_indexes.sql
-- Indexes for performance optimization
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Planning Tables Indexes
-- ----------------------------------------------------------------------------

-- Team abbreviations indexes
CREATE INDEX IF NOT EXISTS idx_team_abbrev_season ON team_abbreviations(season);
CREATE INDEX IF NOT EXISTS idx_team_abbrev_abbr ON team_abbreviations(abbreviation);
CREATE INDEX IF NOT EXISTS idx_team_abbrev_team ON team_abbreviations(team_name);

-- Team histories indexes
CREATE INDEX IF NOT EXISTS idx_team_hist_id ON team_histories(team_id);
CREATE INDEX IF NOT EXISTS idx_team_hist_abbrev ON team_histories(team_abbrev);
CREATE INDEX IF NOT EXISTS idx_team_hist_founded ON team_histories(season_founded);

-- Player master indexes
CREATE INDEX IF NOT EXISTS idx_player_master_name ON player_master(player_name);
CREATE INDEX IF NOT EXISTS idx_player_master_career_start ON player_master(career_start);
CREATE INDEX IF NOT EXISTS idx_player_master_career_end ON player_master(career_end);
CREATE INDEX IF NOT EXISTS idx_player_master_hof ON player_master(hall_of_fame);
CREATE INDEX IF NOT EXISTS idx_player_master_birth ON player_master(birth_date);

-- Player demographics indexes
CREATE INDEX IF NOT EXISTS idx_player_demo_name ON player_demographics(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_player_demo_country ON player_demographics(country);
CREATE INDEX IF NOT EXISTS idx_player_demo_draft ON player_demographics(draft_year);

-- Player season info indexes
CREATE INDEX IF NOT EXISTS idx_player_season_info_player ON player_season_info(player_id);
CREATE INDEX IF NOT EXISTS idx_player_season_info_season ON player_season_info(season);
CREATE INDEX IF NOT EXISTS idx_player_season_info_team ON player_season_info(team);
CREATE INDEX IF NOT EXISTS idx_player_season_info_composite ON player_season_info(season, team);

-- ----------------------------------------------------------------------------
-- Game Tables Indexes
-- ----------------------------------------------------------------------------

-- Games historical indexes
CREATE INDEX IF NOT EXISTS idx_games_hist_date ON games_historical(game_datetime_est);
CREATE INDEX IF NOT EXISTS idx_games_hist_home ON games_historical(home_team_id);
CREATE INDEX IF NOT EXISTS idx_games_hist_away ON games_historical(away_team_id);
CREATE INDEX IF NOT EXISTS idx_games_hist_type ON games_historical(game_type);
CREATE INDEX IF NOT EXISTS idx_games_hist_teams ON games_historical(home_team_id, away_team_id);

-- Player game statistics indexes
CREATE INDEX IF NOT EXISTS idx_player_game_stats_game ON player_game_statistics(game_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_person ON player_game_statistics(person_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_team ON player_game_statistics(player_team_name);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_composite ON player_game_statistics(person_id, game_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_datetime ON player_game_statistics(game_datetime_est);

-- Team game statistics indexes
CREATE INDEX IF NOT EXISTS idx_team_game_stats_game ON team_game_statistics(game_id);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_team ON team_game_statistics(team_id);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_opp ON team_game_statistics(opponent_team_id);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_composite ON team_game_statistics(team_id, game_id);

-- ----------------------------------------------------------------------------
-- Season Stats Tables Indexes
-- ----------------------------------------------------------------------------

-- Player season totals indexes
CREATE INDEX IF NOT EXISTS idx_player_totals_player ON player_season_totals(player_id);
CREATE INDEX IF NOT EXISTS idx_player_totals_season ON player_season_totals(season);
CREATE INDEX IF NOT EXISTS idx_player_totals_team ON player_season_totals(team);
CREATE INDEX IF NOT EXISTS idx_player_totals_composite ON player_season_totals(season, player_id);

-- Player per game indexes
CREATE INDEX IF NOT EXISTS idx_player_per_game_player ON player_season_per_game(player_id);
CREATE INDEX IF NOT EXISTS idx_player_per_game_season ON player_season_per_game(season);
CREATE INDEX IF NOT EXISTS idx_player_per_game_pts ON player_season_per_game(pts_per_game);

-- Player advanced indexes
CREATE INDEX IF NOT EXISTS idx_player_advanced_player ON player_season_advanced(player_id);
CREATE INDEX IF NOT EXISTS idx_player_advanced_season ON player_season_advanced(season);
CREATE INDEX IF NOT EXISTS idx_player_advanced_per ON player_season_advanced(per);
CREATE INDEX IF NOT EXISTS idx_player_advanced_ws ON player_season_advanced(ws);
CREATE INDEX IF NOT EXISTS idx_player_advanced_bpm ON player_season_advanced(bpm);

-- Player per 100 indexes
CREATE INDEX IF NOT EXISTS idx_player_per_100_player ON player_season_per_100(player_id);
CREATE INDEX IF NOT EXISTS idx_player_per_100_season ON player_season_per_100(season);

-- Player per 36 indexes
CREATE INDEX IF NOT EXISTS idx_player_per_36_player ON player_season_per_36(player_id);
CREATE INDEX IF NOT EXISTS idx_player_per_36_season ON player_season_per_36(season);

-- Player shooting indexes
CREATE INDEX IF NOT EXISTS idx_player_shooting_player ON player_season_shooting(player_id);
CREATE INDEX IF NOT EXISTS idx_player_shooting_season ON player_season_shooting(season);
CREATE INDEX IF NOT EXISTS idx_player_shooting_fg_pct ON player_season_shooting(fg_pct);

-- Player play by play indexes
CREATE INDEX IF NOT EXISTS idx_player_pbp_player ON player_season_play_by_play(player_id);
CREATE INDEX IF NOT EXISTS idx_player_pbp_season ON player_season_play_by_play(season);

-- Team season totals indexes
CREATE INDEX IF NOT EXISTS idx_team_totals_season ON team_season_totals(season);
CREATE INDEX IF NOT EXISTS idx_team_totals_abbr ON team_season_totals(abbreviation);
CREATE INDEX IF NOT EXISTS idx_team_totals_playoff ON team_season_totals(is_playoff);

-- Team season summaries indexes
CREATE INDEX IF NOT EXISTS idx_team_summaries_season ON team_season_summaries(season);
CREATE INDEX IF NOT EXISTS idx_team_summaries_abbr ON team_season_summaries(abbreviation);
CREATE INDEX IF NOT EXISTS idx_team_summaries_wins ON team_season_summaries(wins);
CREATE INDEX IF NOT EXISTS idx_team_summaries_net_rtg ON team_season_summaries(net_rating);

-- Opponent season totals indexes
CREATE INDEX IF NOT EXISTS idx_opp_totals_season ON opponent_season_totals(season);
CREATE INDEX IF NOT EXISTS idx_opp_totals_abbr ON opponent_season_totals(abbreviation);

-- ----------------------------------------------------------------------------
-- Awards Tables Indexes
-- ----------------------------------------------------------------------------

-- All-Star selections indexes
CREATE INDEX IF NOT EXISTS idx_allstar_season ON all_star_selections(season);
CREATE INDEX IF NOT EXISTS idx_allstar_player ON all_star_selections(player_id);

-- End of season teams indexes
CREATE INDEX IF NOT EXISTS idx_eos_teams_season ON end_of_season_teams(season);
CREATE INDEX IF NOT EXISTS idx_eos_teams_player ON end_of_season_teams(player_id);
CREATE INDEX IF NOT EXISTS idx_eos_teams_type ON end_of_season_teams(team_type);

-- End of season teams voting indexes
CREATE INDEX IF NOT EXISTS idx_eos_voting_season ON end_of_season_teams_voting(season);
CREATE INDEX IF NOT EXISTS idx_eos_voting_player ON end_of_season_teams_voting(player_id);
CREATE INDEX IF NOT EXISTS idx_eos_voting_share ON end_of_season_teams_voting(share);

-- Player award shares indexes
CREATE INDEX IF NOT EXISTS idx_award_shares_season ON player_award_shares(season);
CREATE INDEX IF NOT EXISTS idx_award_shares_player ON player_award_shares(player_id);
CREATE INDEX IF NOT EXISTS idx_award_shares_award ON player_award_shares(award_name);
CREATE INDEX IF NOT EXISTS idx_award_shares_winner ON player_award_shares(is_winner);

-- Draft pick history indexes
CREATE INDEX IF NOT EXISTS idx_draft_season ON draft_pick_history(season);
CREATE INDEX IF NOT EXISTS idx_draft_player ON draft_pick_history(player_id);
CREATE INDEX IF NOT EXISTS idx_draft_team ON draft_pick_history(team);
CREATE INDEX IF NOT EXISTS idx_draft_overall ON draft_pick_history(overall_pick);

-- ----------------------------------------------------------------------------
-- ID Mapping Tables Indexes
-- ----------------------------------------------------------------------------

-- Player ID mapping indexes
CREATE INDEX IF NOT EXISTS idx_player_mapping_person ON player_id_mapping(person_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_player ON player_id_mapping(player_id);
CREATE INDEX IF NOT EXISTS idx_player_mapping_verified ON player_id_mapping(is_verified);

-- Team ID mapping indexes
CREATE INDEX IF NOT EXISTS idx_team_mapping_id ON team_id_mapping(team_id);
CREATE INDEX IF NOT EXISTS idx_team_mapping_season ON team_id_mapping(season);
CREATE INDEX IF NOT EXISTS idx_team_mapping_abbrev ON team_id_mapping(team_abbrev);

-- Data source tracking indexes
CREATE INDEX IF NOT EXISTS idx_source_tracking_table ON data_source_tracking(table_name);
CREATE INDEX IF NOT EXISTS idx_source_tracking_file ON data_source_tracking(source_file);
CREATE INDEX IF NOT EXISTS idx_source_tracking_batch ON data_source_tracking(ingestion_batch_id);
CREATE INDEX IF NOT EXISTS idx_source_tracking_status ON data_source_tracking(validation_status);

-- Ingestion log indexes
CREATE INDEX IF NOT EXISTS idx_ingestion_log_batch ON ingestion_log(batch_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_table ON ingestion_log(table_name);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_started ON ingestion_log(started_at);
