"""Compatibility facade for stats helpers.

The implementation is split by responsibility, while routes keep importing
services.stats with the existing function names.
"""
from services.stats_aggregates import *
from services.stats_records import *
from services.stats_reports import *

# Keep selected private names available for existing tests/tools.
from services.stats_aggregates import _UNSET, _calc_streak, _fetch_matches, _latest_lp, _latest_mr
from services.stats_records import _compute_all_streaks
