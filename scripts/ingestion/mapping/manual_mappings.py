"""Manual mappings for edge cases in ID resolution."""

MANUAL_PLAYER_MAPPINGS = {
    43217: "olivinha01",
    196294611: None,
    1627114: "abercto01",
    196294573: None,
    203518: "abrinal01",
    56017: None,
}

TEAM_NAME_NORMALIZATIONS = {
    "LA Clippers": "Los Angeles Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "New Orleans Hornets": "New Orleans Pelicans",
    "Charlotte Bobcats": "Charlotte Hornets",
    "Portland Trailblazers": "Portland Trail Blazers",
}

FRANCHISE_MAPPINGS = {
    "SEA": "OKC",
    "VAN": "MEM",
    "NJN": "BKN",
    "NJ": "BKN",
}

TEAM_ABBREV_HISTORY = {
    "NJ": {"team_id": 1610612751, "seasons": (1977, 2011)},
    "NJN": {"team_id": 1610612751, "seasons": (1977, 2011)},
    "BKN": {"team_id": 1610612751, "seasons": (2012, 2100)},
    "BRK": {"team_id": 1610612751, "seasons": (2012, 2100)},
    "CHA": {"team_id": 1610612766, "seasons": (1989, 2100)},
    "CHH": {"team_id": 1610612766, "seasons": (1989, 2002)},
    "CHO": {"team_id": 1610612766, "seasons": (2015, 2100)},
    "NOH": {"team_id": 1610612740, "seasons": (2002, 2012)},
    "NOK": {"team_id": 1610612740, "seasons": (2005, 2006)},
    "NOP": {"team_id": 1610612740, "seasons": (2013, 2100)},
    "SEA": {"team_id": 1610612760, "seasons": (1967, 2008)},
    "OKC": {"team_id": 1610612760, "seasons": (2009, 2100)},
    "VAN": {"team_id": 1610612763, "seasons": (1996, 2001)},
    "MEM": {"team_id": 1610612763, "seasons": (2002, 2100)},
}

CONFIDENCE_THRESHOLDS = {
    "exact_name_match": 1.0,
    "fuzzy_name_match_high": 0.95,
    "fuzzy_name_match_medium": 0.85,
    "fuzzy_name_match_low": 0.75,
    "manual_mapping": 1.0,
}

MATCH_TYPES = {
    "exact": "exact_name_match",
    "fuzzy_high": "fuzzy_match_high_confidence",
    "fuzzy_medium": "fuzzy_match_medium_confidence",
    "fuzzy_low": "fuzzy_match_low_confidence",
    "manual": "manual_override",
    "unmatched": "unmatched",
}
