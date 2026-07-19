import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import shutil
import uuid
import csv
import logging
import json
import gc
from datetime import datetime
from flask import Flask, render_template, request, url_for, redirect, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

# 1. Enhanced Logging Configuration
# Includes timestamps and severity levels for better debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = app.logger

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STATIC_FOLDER'] = 'static'
app.config['DATA_FOLDER'] = 'data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16MB
HISTORY_FILE = os.path.join(app.config['DATA_FOLDER'], 'history.csv')
STATES_FILE = os.path.join(app.config['DATA_FOLDER'], 'states.json')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
os.makedirs(app.config['DATA_FOLDER'], exist_ok=True)

# THE STANDARD COLUMNS WE EXPECT
HISTORY_COLUMNS = [
    'Date',
    'Baseline_Alpha', 'Entrained_Alpha', 'Responsiveness_Index',
    'Baseline_RMSSD', 'Entrained_RMSSD', 'Power',
    'Entrained_Resp_Rate',
    'Plot_File',
    'Baseline_HR', 'Baseline_Mean_RR'
]

# Legacy column names mapped to their current equivalents. Schema migration
# must RENAME these (never add-empty-and-drop), or historical values are lost
# when a metric is renamed.
LEGACY_COLUMN_RENAMES = {
    'Normal_Alpha': 'Baseline_Alpha',
    'Normal_RMSSD': 'Baseline_RMSSD',
    'ratio': 'Responsiveness_Index',
    'Coherence_Index': 'Responsiveness_Index',
    'Vagal_Gain': 'Power',
}

# In-memory cache for history to avoid re-reading CSV on every request
_history_cache = {'data': None, 'mtime': None}

# Initialize history file if needed
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(HISTORY_COLUMNS)

# Load State Definitions
STATE_DEFINITIONS = {}
def load_state_definitions():
    """Load state definitions from JSON file into global dictionary."""
    global STATE_DEFINITIONS
    if os.path.exists(STATES_FILE):
        try:
            with open(STATES_FILE, 'r') as f:
                STATE_DEFINITIONS = json.load(f)
            logger.info("State definitions loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading state definitions: {e}")
    else:
        logger.warning("states.json not found. Using defaults might fail if not handled.")

# Load on startup
load_state_definitions()

# ============================================================================
# PHASE 2: USER PROFILES (Per-user parameters stored in JSON)
# ============================================================================
USER_PROFILES_FILE = os.path.join(app.config['DATA_FOLDER'], 'user_profiles.json')
USER_PROFILES = {}

def load_user_profiles():
    """Load user profiles from JSON file."""
    global USER_PROFILES
    if os.path.exists(USER_PROFILES_FILE):
        try:
            with open(USER_PROFILES_FILE, 'r') as f:
                data = json.load(f)
                USER_PROFILES = {u['user_id']: u for u in data.get('users', [])}
            logger.info(f"Loaded {len(USER_PROFILES)} user profiles.")
        except Exception as e:
            logger.error(f"Error loading user profiles: {e}")
    else:
        logger.warning("user_profiles.json not found.")

def save_user_profiles():
    """Save user profiles to JSON file."""
    try:
        with open(USER_PROFILES_FILE, 'w') as f:
            json.dump({'users': list(USER_PROFILES.values())}, f, indent=2)
        logger.info(f"Saved {len(USER_PROFILES)} user profiles.")
    except Exception as e:
        logger.error(f"Error saving user profiles: {e}")

def get_or_create_user_profile(user_id='default'):
    """Get or create user profile with defaults."""
    if user_id not in USER_PROFILES:
        # Create new profile with Phase 1 constants as defaults
        USER_PROFILES[user_id] = {
            'user_id': user_id,
            'session_count': 0,
            'personalization_phase': 1,
            'responsiveness_threshold_computed': RESPONSIVENESS_TIEBREAKER_DEFAULT,
            'responsiveness_threshold_source': 'phase_1_default',
            'rmssd_ceiling_computed': 40.0,
            'rmssd_ceiling_source': 'phase_1_default',
            'baseline_rmssd_mean': None,
            'baseline_rmssd_sd': None,
            'baseline_hr_mean': None,
            'baseline_hr_sd': None,
            'baseline_hr_source': None,
            'thresholds_last_computed': datetime.now().isoformat() + 'Z',
            'thresholds_computed_from_n': 0,
            'last_session_date': None
        }
        save_user_profiles()
    return USER_PROFILES[user_id]

def compute_responsiveness_threshold_from_history(history_file, window_sessions=30, df=None):
    """Compute 90th percentile of responsiveness ratio from trailing sessions.

    Accepts an optional preloaded DataFrame (df) to avoid re-reading the CSV
    when several threshold computations run back-to-back.
    """
    try:
        if df is None:
            df = pd.read_csv(history_file, skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]

        if 'Responsiveness_Index' not in df.columns or len(df) == 0:
            return None

        # Get trailing window of responsiveness values
        responsiveness_vals = pd.to_numeric(df['Responsiveness_Index'].tail(window_sessions), errors='coerce')
        responsiveness_vals = responsiveness_vals.dropna()

        if len(responsiveness_vals) < 5:
            return None

        # Return 90th percentile
        return round(np.percentile(responsiveness_vals, 90), 2)
    except Exception as e:
        logger.warning(f"Could not compute responsiveness threshold: {e}")
        return None

def compute_rmssd_ceiling_from_history(history_file, window_sessions=30, df=None):
    """Compute 90th percentile of entrained RMSSD from trailing sessions.

    Accepts an optional preloaded DataFrame (df) to avoid re-reading the CSV.
    """
    try:
        if df is None:
            df = pd.read_csv(history_file, skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]

        if 'Entrained_RMSSD' not in df.columns or len(df) == 0:
            return None

        # Get trailing window of entrained RMSSD values
        rmssd_vals = pd.to_numeric(df['Entrained_RMSSD'].tail(window_sessions), errors='coerce')
        rmssd_vals = rmssd_vals.dropna()

        if len(rmssd_vals) < 5:
            return None

        # Return 90th percentile
        return round(np.percentile(rmssd_vals, 90), 1)
    except Exception as e:
        logger.warning(f"Could not compute RMSSD ceiling: {e}")
        return None

def compute_baseline_norms_from_history(history_file, df=None):
    """Compute mean and SD of baseline RMSSD and baseline HR from all sessions.

    Accepts an optional preloaded DataFrame (df) to avoid re-reading the CSV.
    """
    try:
        if df is None:
            df = pd.read_csv(history_file, skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]

        results = {}

        # Baseline RMSSD norms
        if 'Baseline_RMSSD' in df.columns:
            b_rmssd = pd.to_numeric(df['Baseline_RMSSD'], errors='coerce').dropna()
            if len(b_rmssd) > 2:
                results['baseline_rmssd_mean'] = round(b_rmssd.mean(), 1)
                results['baseline_rmssd_sd'] = round(b_rmssd.std(), 1)

        # Baseline HR norms
        if 'Baseline_HR' in df.columns:
            b_hr = pd.to_numeric(df['Baseline_HR'], errors='coerce').dropna()
            if len(b_hr) > 2:
                results['baseline_hr_mean'] = round(b_hr.mean(), 1)
                results['baseline_hr_sd'] = round(b_hr.std(), 1)

        return results if results else None
    except Exception as e:
        logger.warning(f"Could not compute baseline norms: {e}")
        return None

def update_user_profile(user_id='default'):
    """Update user profile after new session (recompute thresholds and personal norms)."""
    profile = get_or_create_user_profile(user_id)

    # Load history once and reuse it for every threshold computation below,
    # instead of each helper re-reading and re-parsing the same CSV.
    hist_df = None
    try:
        hist_df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
        hist_df.columns = [c.strip() for c in hist_df.columns]
    except Exception as e:
        logger.warning(f"Could not load history for profile update: {e}")

    # Recompute thresholds from history
    new_responsiveness = compute_responsiveness_threshold_from_history(HISTORY_FILE, CEILING_WINDOW_SESSIONS, df=hist_df)
    new_rmssd = compute_rmssd_ceiling_from_history(HISTORY_FILE, CEILING_WINDOW_SESSIONS, df=hist_df)
    baseline_norms = compute_baseline_norms_from_history(HISTORY_FILE, df=hist_df)
    floor_mean, floor_sd = compute_baseline_rmssd_stats(HISTORY_FILE, CEILING_WINDOW_SESSIONS, df=hist_df)

    if new_responsiveness is not None:
        profile['responsiveness_threshold_computed'] = new_responsiveness
        profile['responsiveness_threshold_source'] = 'personal_rolling_90th_percentile'

    if new_rmssd is not None:
        profile['rmssd_ceiling_computed'] = new_rmssd
        profile['rmssd_ceiling_source'] = 'personal_rolling_90th_percentile'

    # Depleted-floor stats: stored from the TRAILING window (same recency logic
    # as the rolling ceiling) with a >=5-session minimum, so the override can
    # never arm off 2-3 noisy points. Reset to None when history drops below
    # the minimum (e.g. after deletions) so the override disarms cleanly.
    profile['baseline_rmssd_mean'] = round(floor_mean, 1) if floor_mean is not None else None
    profile['baseline_rmssd_sd'] = round(floor_sd, 1) if floor_sd is not None else None

    # Update baseline HR personal norms (for Tier B classifier)
    if baseline_norms:
        profile['baseline_hr_mean'] = baseline_norms.get('baseline_hr_mean')
        profile['baseline_hr_sd'] = baseline_norms.get('baseline_hr_sd')
        profile['baseline_hr_source'] = 'backfilled_from_raw_rr'

    # Update metadata
    session_count = len(hist_df) if hist_df is not None else 0
    if hist_df is not None:
        # Only overwrite when history actually loaded, so a transient read
        # failure can't reset a real count to 0.
        profile['session_count'] = session_count
    profile['thresholds_last_computed'] = datetime.now().isoformat() + 'Z'
    profile['thresholds_computed_from_n'] = session_count
    profile['last_session_date'] = datetime.now().isoformat() + 'Z'

    # Auto-transition to Phase 2 at threshold
    if profile['session_count'] >= 15 and profile['personalization_phase'] == 1:
        profile['personalization_phase'] = 2
        logger.info(f"User {user_id} auto-transitioned to Phase 2 (personalized mode)")

    save_user_profiles()

# Load profiles on startup
load_user_profiles()

# ============================================================================
# PHASE 1: CLASSIFIER CONSTANTS (placeholder priors for proof of concept)
# ============================================================================
# Version tracking: what basis do these constants represent?
THRESHOLDS_VERSION = "v1.0: placeholder priors, no population data"

# HEADROOM_FLOOR_MS = 3
# Source: engineering constraint (prevents denominator explosion when
#   baseline RMSSD approaches or exceeds rolling ceiling).
#   Not empirically derived; chosen to maintain numerical stability.
#   Revisit if sessions with baseline near ceiling become common.
HEADROOM_FLOOR_MS = 3

# HEADROOM_CAP = 2.0
# Source: round-number prior. Prevents runaway scores when denominator
#   shrinks (e.g., baseline near ceiling). No population data.
#   Tune as multi-user data accumulates.
HEADROOM_CAP = 2.0

# CEILING_PERCENTILE = 90
# Source: statistical convention. Rolling 90th percentile of personal
#   entrained RMSSD. Grounded in user's own history once window fills.
#   No published population basis for this specific percentile.
CEILING_PERCENTILE = 90

# FLOOR_Z_THRESHOLD = -2.0
# Source: statistical convention. The depleted-floor override fires when a
#   session's BASELINE RMSSD sits this many standard deviations (or more)
#   BELOW the user's own mean baseline RMSSD — i.e., a severe personal
#   departure, not merely the low end of a healthy spread.
#   Why z-score, not a percentile: a percentile floor (e.g. 10th) fires on a
#   FIXED fraction of every user's sessions by construction, flagging ~10%
#   even of a perfectly healthy person. A z-score fires only on genuine
#   departures, so a stable user may go long stretches without ever tripping
#   it. Why not a hardcoded ms value: an absolute floor misclassifies anyone
#   whose normal resting RMSSD differs from the reference person.
#   -2.0 chosen (vs -1.5) to trap only SEVERE departures, since the override
#   promotes to a red "Running on Fumes" state. Cold-start safe: mean/SD are
#   not computed until history exists, so the override simply does not fire
#   for new users.
FLOOR_Z_THRESHOLD = -2.0

# CEILING_WINDOW_SESSIONS = 30
# Source: judgment call. Balances recency (captures current physiology)
#   vs stability (enough data to compute percentile robustly).
#   No empirical basis. May need adjustment for infrequent users.
CEILING_WINDOW_SESSIONS = 30

# RESPONSIVENESS_TIEBREAKER_DEFAULT = 2.4
# Source: placeholder prior. NOT a population threshold.
#   Cold-start fallback only.
#   Used as cold-start fallback only. Will be replaced at runtime by
#   each user's own rolling 90th percentile of responsiveness ratio once
#   sufficient history exists (see compute_responsiveness_tiebreaker_threshold()).
#   CRITICAL: Do not treat as universal or apply to other users.
RESPONSIVENESS_TIEBREAKER_DEFAULT = 2.4

# POWER_THRESHOLD = 1.5
# Source: round-number prior. No published basis for this specific
#   value in resting paced-breathing entrainment context.
#   Borrowed loosely from HRV fold-change conventions.
#   HIGH PRIORITY for empirical grounding as multi-user data accumulates.
POWER_THRESHOLD = 1.5

# POWER_MARGIN_PCT = 0.90
# Source: judgment call. Defines "near-miss" as gain >= threshold * 0.90
#   (i.e., within 10% of threshold). Prevents tiebreaker from rescuing
#   sessions with genuinely low amplitude. No empirical basis.
POWER_MARGIN_PCT = 0.90

# RESPONSIVENESS_THRESHOLD = 1.2
# Source: round-number prior. No published basis for resting paced-
#   breathing context. Same caveat as POWER_THRESHOLD.
RESPONSIVENESS_THRESHOLD = 1.2

def compute_rolling_ceiling(history_file, window_sessions=30):
    """
    Compute 90th percentile of Entrained_RMSSD from trailing window.
    Returns ceiling value or None if insufficient data.
    """
    try:
        if not os.path.exists(history_file):
            return None

        df = pd.read_csv(history_file, skipinitialspace=True)
        if df.empty or len(df) < 5:
            return None

        # Get last N sessions
        trailing = df.tail(window_sessions)
        entrained_vals = pd.to_numeric(trailing['Entrained_RMSSD'], errors='coerce').dropna()

        if len(entrained_vals) < 5:
            return None

        ceiling = np.percentile(entrained_vals, CEILING_PERCENTILE)
        return ceiling
    except Exception as e:
        logger.error(f"Error computing rolling ceiling: {e}")
        return None

def compute_baseline_rmssd_stats(history_file, window_sessions=30, df=None):
    """
    Compute (mean, sd) of Baseline_RMSSD from the trailing window.
    Returns (mean, sd) or (None, None) if insufficient data.

    Used by the depleted-floor override, which fires when a session's baseline
    RMSSD sits FLOOR_Z_THRESHOLD SDs (or more) below this personal mean — a
    severe departure FOR THIS USER, not a fixed fraction of sessions and not an
    absolute cutoff. Returns (None, None) when history is thin, so the override
    is disabled for new users rather than guessing.

    Accepts an optional preloaded DataFrame (df) to avoid re-reading the CSV.
    The df must be in file (chronological) order so tail() is the recent window.
    """
    try:
        if df is None:
            if not os.path.exists(history_file):
                return None, None
            df = pd.read_csv(history_file, skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]

        if df.empty or len(df) < 5 or 'Baseline_RMSSD' not in df.columns:
            return None, None

        trailing = df.tail(window_sessions)
        baseline_vals = pd.to_numeric(trailing['Baseline_RMSSD'], errors='coerce').dropna()

        if len(baseline_vals) < 5:
            return None, None

        mean = baseline_vals.mean()
        sd = baseline_vals.std()  # sample SD (ddof=1)
        if pd.isna(sd) or sd <= 0:
            return None, None
        return mean, sd
    except Exception as e:
        logger.error(f"Error computing baseline RMSSD stats: {e}")
        return None, None

def compute_responsiveness_tiebreaker_threshold(history_file, window_sessions=None):
    """
    Compute 90th percentile of Responsiveness Ratio from trailing window.
    Returns computed threshold or RESPONSIVENESS_TIEBREAKER_DEFAULT if insufficient data.

    CRITICAL: This is a per-user adaptive threshold. It will differ for each user.
    Only the fallback default (RESPONSIVENESS_TIEBREAKER_DEFAULT) is universal.
    """
    try:
        if not os.path.exists(history_file):
            return RESPONSIVENESS_TIEBREAKER_DEFAULT

        df = pd.read_csv(history_file, skipinitialspace=True)
        if df.empty or len(df) < 10:  # Need more data for responsiveness percentile
            return RESPONSIVENESS_TIEBREAKER_DEFAULT

        # Get last N sessions (use same window as ceiling for consistency)
        if window_sessions is None:
            window_sessions = CEILING_WINDOW_SESSIONS

        trailing = df.tail(window_sessions)

        # Compute responsiveness ratio for each session
        b_alpha = pd.to_numeric(trailing['Baseline_Alpha'], errors='coerce').dropna()
        e_alpha = pd.to_numeric(trailing['Entrained_Alpha'], errors='coerce').dropna()

        if len(b_alpha) < 5 or len(e_alpha) < 5 or len(b_alpha) != len(e_alpha):
            return RESPONSIVENESS_TIEBREAKER_DEFAULT

        # Compute responsiveness ratio, handle division
        responsiveness_ratios = []
        for i in range(min(len(b_alpha), len(e_alpha))):
            if b_alpha.iloc[i] > 0.001:  # Avoid division by zero
                responsiveness_ratios.append(e_alpha.iloc[i] / b_alpha.iloc[i])

        if len(responsiveness_ratios) < 5:
            return RESPONSIVENESS_TIEBREAKER_DEFAULT

        threshold = np.percentile(responsiveness_ratios, CEILING_PERCENTILE)
        return threshold
    except Exception as e:
        logger.error(f"Error computing responsiveness tiebreaker threshold: {e}")
        return RESPONSIVENESS_TIEBREAKER_DEFAULT

# --- 12-STATE "INTEGRATION & DYNAMICS" LOGIC (v2) ---
# Classification is based on a 2x2 response matrix (Responsiveness Ratio x Power)
# with Tier context (Baseline Alpha) modifying the meaning of each cell.
# Entrained Alpha is now a reported output only — not a classifier.
#
# 2x2 Core:
#   Power > 1.5 + Responsiveness > 1.2  →  Full Response  (Flow / Reserves / Laser)
#   Power > 1.5 + Responsiveness < 1.2  →  Vagal Brake    (energy without organization)
#   Power < 1.5 + Responsiveness > 1.2  →  Fragile Calm   (structure without amplitude)
#   Power < 1.5 + Responsiveness < 1.2  →  No Response    (Burned Out / Stuck / Fumes)
#
# Special Override (applied first):
#   b_rmssd > 30 + Responsiveness > 1.2 →  Vagal Wave    (ceiling effect)

def get_interpretation(b_alpha, e_alpha, b_rmssd, e_rmssd, user_profile=None):
    """
    Classifies user state using the 2x2 Response Matrix + Tier context framework.

    PHASE 1: Proof of Concept with three fixes:
    1. Floor + cap on headroom (prevents denominator explosion)
    2. Rolling ceiling (90th percentile of entrained RMSSD, trailing window)
    3. Responsiveness tiebreaker (strong responsiveness rescues near-miss power)

    PHASE 2: Per-user thresholds from user_profile (optional).

    Args:
        b_alpha (float): Baseline DFA Alpha-1
        e_alpha (float): Entrained DFA Alpha-1 (reported only, not used for classification)
        b_rmssd (float): Baseline RMSSD
        e_rmssd (float): Entrained RMSSD
        user_profile (dict, optional): User profile with computed thresholds. If None, uses Phase 1 defaults.

    Returns:
        dict: Dictionary containing state name, physiology, implication, goal, and color.
    """
    # Safety zeros to prevent division errors
    b_alpha = max(b_alpha, 0.001)
    b_rmssd = max(b_rmssd, 0.001)

    responsiveness_ratio = e_alpha / b_alpha
    power = e_rmssd / b_rmssd  # Fold-change gain (for classifier and tiebreaker)

    # === FIX 2: Compute Rolling Ceiling ===
    # Use user profile's computed ceiling if available, else compute from history
    if user_profile and user_profile.get('rmssd_ceiling_computed'):
        ceiling = user_profile['rmssd_ceiling_computed']
    else:
        ceiling = compute_rolling_ceiling(HISTORY_FILE, CEILING_WINDOW_SESSIONS)

    # === Compute Baseline-RMSSD Departure Stats (personal mean & SD) ===
    # Prefer the profile's stored norms; else compute from history. Stay (None,
    # None) when history is thin — the depleted-floor override then does not fire.
    if user_profile and user_profile.get('baseline_rmssd_mean') and user_profile.get('baseline_rmssd_sd'):
        b_rmssd_mean = user_profile['baseline_rmssd_mean']
        b_rmssd_sd = user_profile['baseline_rmssd_sd']
    else:
        b_rmssd_mean, b_rmssd_sd = compute_baseline_rmssd_stats(HISTORY_FILE, CEILING_WINDOW_SESSIONS)

    # === FIX 3 (prep): Compute Responsiveness Tiebreaker Threshold ===
    # Use user profile's computed threshold if available, else compute from history
    if user_profile and user_profile.get('responsiveness_threshold_computed'):
        responsiveness_tiebreaker_threshold = user_profile['responsiveness_threshold_computed']
    else:
        responsiveness_tiebreaker_threshold = compute_responsiveness_tiebreaker_threshold(HISTORY_FILE, CEILING_WINDOW_SESSIONS)

    # If insufficient history, use all-time 90th as fallback
    if ceiling is None:
        try:
            df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
            if not df.empty:
                all_entrained = pd.to_numeric(df['Entrained_RMSSD'], errors='coerce').dropna()
                ceiling = np.percentile(all_entrained, CEILING_PERCENTILE) if len(all_entrained) > 0 else 40.0
            else:
                ceiling = 40.0  # placeholder cold-start default
        except Exception:
            ceiling = 40.0  # placeholder cold-start default

    # === FIX 1: Compute Headroom with Floor + Cap (for diagnostics, prevents denominator explosion) ===
    denom = max(ceiling - b_rmssd, HEADROOM_FLOOR_MS)
    headroom = min((e_rmssd - b_rmssd) / denom, HEADROOM_CAP)

    # Identify the key based on logic
    key = "unknown"

    # --- SPECIAL OVERRIDE: DEPLETED FLOOR (checked first) ---
    # Fires when today's baseline RMSSD is a SEVERE departure below the user's
    # own mean (z <= FLOOR_Z_THRESHOLD, i.e. -2.0 SD). At such a low resting
    # floor the gain ratio's denominator is tiny, so even a modest absolute
    # rise yields a large relative gain — the ratios stop being trustworthy and
    # can mask genuine depletion. We surface that honestly rather than award a
    # green state. Fully relative (z-score in the user's own units), so it
    # generalizes across people and never fires on a fixed fraction of sessions.
    # Disabled at cold start (mean/SD are None until enough history exists).
    if (b_rmssd_mean is not None and b_rmssd_sd is not None and b_rmssd_sd > 0
            and (b_rmssd - b_rmssd_mean) / b_rmssd_sd <= FLOOR_Z_THRESHOLD):
        key = "running_on_fumes"

    # --- SPECIAL OVERRIDE: VAGAL WAVE ---
    # Baseline RMSSD near the top of this user's own range compresses relative
    # gain — a ceiling effect, not a failure. Uses the personal rolling ceiling
    # (90th percentile) rather than a hardcoded 30 ms so it generalizes across
    # users. Falls back to the ceiling value resolved above when no profile.
    elif b_rmssd >= ceiling and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
        key = "surfing_the_wave"

    # --- TIER III: HIGH BASELINE (b_alpha > 1.25) ---
    elif b_alpha > 1.25:
        if power >= POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "laser_focus"          # Full response from high base
        elif power >= POWER_THRESHOLD and responsiveness_ratio < RESPONSIVENESS_THRESHOLD:
            key = "tug_of_war"           # Vagal Brake — energy without structure
        elif power < POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "attentive"            # Structure held, no vagal recruitment
        else:
            key = "stuck"                # No response in either axis

    # --- TIER I: LOW BASELINE (b_alpha < 0.75) ---
    elif b_alpha < 0.75:
        if power >= POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "relying_on_reserves"  # Full response despite low base
        elif power >= POWER_THRESHOLD and responsiveness_ratio < RESPONSIVENESS_THRESHOLD:
            key = "running_low"          # Vagal Brake on depleted system
        # === FIX 3: Responsiveness Tiebreaker (rescue near-miss sessions) ===
        # Responsiveness in top decile AND fold-change gain is near-miss (within margin of threshold)
        elif (power < POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD and
              responsiveness_ratio >= responsiveness_tiebreaker_threshold and
              power >= (POWER_THRESHOLD * POWER_MARGIN_PCT)):
            key = "relying_on_reserves"  # Rescued by strong responsiveness + near-miss power
        elif power < POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "fragile_calm"         # Structure shifted, amplitude limited
        else:
            key = "running_on_fumes"     # No response — system is depleted

    # --- TIER II: AVAILABLE BASELINE (0.75 <= b_alpha <= 1.25) ---
    else:
        if power >= POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "feeling_the_flow"     # Full response — optimal state
        elif power >= POWER_THRESHOLD and responsiveness_ratio < RESPONSIVENESS_THRESHOLD:
            key = "tug_of_war"           # Vagal Brake — energy without structure
        # === FIX 3: Responsiveness Tiebreaker (rescue near-miss sessions) ===
        # Responsiveness in top decile AND fold-change gain is near-miss (within margin of threshold)
        elif (power < POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD and
              responsiveness_ratio >= responsiveness_tiebreaker_threshold and
              power >= (POWER_THRESHOLD * POWER_MARGIN_PCT)):
            key = "feeling_the_flow"     # Rescued by strong responsiveness + near-miss power
        elif power < POWER_THRESHOLD and responsiveness_ratio >= RESPONSIVENESS_THRESHOLD:
            key = "fragile_calm"         # Structure shifted, amplitude limited
        else:
            key = "burned_out"           # No response — system perceived stress

    # Retrieve data from JSON
    raw_data = STATE_DEFINITIONS.get(key, STATE_DEFINITIONS.get("unknown", {}))

    # We copy to avoid mutating the global dictionary
    data = raw_data.copy()

    # Format the strings with actual numbers
    fmt_args = {
        "b_alpha": f"{b_alpha:.2f}",
        "e_alpha": f"{e_alpha:.2f}",
        "power": f"{power:.2f}",
        "responsiveness_ratio": f"{responsiveness_ratio:.2f}",
        "b_rmssd": f"{b_rmssd:.1f}",
        "e_rmssd": f"{e_rmssd:.1f}",
        "headroom": f"{headroom:.2f}",
        "ceiling": f"{ceiling:.1f}"
    }

    try:
        if "physiology" in data:
            data["physiology"] = data["physiology"].format(**fmt_args)
        if "implication" in data:
            data["implication"] = data["implication"].format(**fmt_args)
    except Exception as e:
        logger.error(f"Error formatting state strings: {e}")
        pass

    # Ensure defaults if keys missing
    if "color" not in data: data["color"] = "secondary"
    if "state" not in data: data["state"] = "Unknown"

    return data

class AutonomicFlexibilityAnalyzer:
    """
    Analyzer class for processing RR interval data and generating autonomic flexibility metrics.
    """
    def __init__(self, baseline_path, entrained_path):
        self.baseline_df = self._load_df(baseline_path)
        self.entrained_df = self._load_df(entrained_path)
        
        # Check for Auto-Split Condition (Same file uploaded twice)
        self._check_and_split_single_file()

        self.results = {}

    def _load_df(self, filepath):
        """Load CSV into DataFrame with error handling."""
        try:
            return pd.read_csv(filepath, skipinitialspace=True)
        except Exception as e:
            logger.error(f"Error loading DataFrame from {filepath}: {e}")
            return pd.DataFrame()

    def _check_and_split_single_file(self):
        """
        If the user uploads the same file to both inputs (simulating a single-file workflow),
        we look for a significant time gap (>10 seconds) to split the session automatically.
        """
        if self.baseline_df.empty or self.entrained_df.empty:
            return

        # Simple check: are they the exact same size and content?
        if len(self.baseline_df) == len(self.entrained_df) and self.baseline_df.equals(self.entrained_df):
            logger.info("Identical files detected. Attempting to auto-split based on time gap.")
            
            df = self.baseline_df
            
            # Find time column
            time_cols = [c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()]
            timestamp_col = time_cols[0] if time_cols else None
            
            if timestamp_col:
                # Try to parse timestamps
                try:
                    # Convert to datetime objects if they are strings
                    times = pd.to_datetime(df[timestamp_col], errors='coerce')
                    
                    # If conversion failed (e.g., it's just seconds/milliseconds numbers), handle numeric
                    if times.isna().all():
                         times = pd.to_numeric(df[timestamp_col], errors='coerce')
                    
                    # Calculate differences
                    diffs = np.diff(times)

                    if len(diffs) == 0:
                        logger.warning("Not enough timestamps to compute gaps for auto-split.")
                        return

                    # If datetime objects, diffs are Timedeltas, convert to seconds
                    if hasattr(diffs[0], 'total_seconds'):
                        diffs = [d.total_seconds() for d in diffs]
                    
                    # Look for a gap > 10 seconds (arbitrary "break" threshold)
                    gap_indices = np.where(np.array(diffs) > 10)[0]
                    
                    if len(gap_indices) > 0:
                        split_idx = gap_indices[0] + 1 # +1 because diff is n-1
                        
                        # Apply Split
                        self.baseline_df = df.iloc[:split_idx].reset_index(drop=True)
                        self.entrained_df = df.iloc[split_idx:].reset_index(drop=True)
                        
                        logger.info(f"Auto-split successful at index {split_idx}. Baseline: {len(self.baseline_df)}, Entrained: {len(self.entrained_df)}")
                    else:
                        logger.warning("No significant time gap found to split the file.")
                except Exception as e:
                    logger.error(f"Failed to auto-split file: {e}")

    def get_rr_values(self, df):
        """Extract RR intervals from DataFrame."""
        if df.empty: return []
        rr_col = [c for c in df.columns if 'rr' in c.lower().strip()]
        if not rr_col: return []
        return df[rr_col[0]].values

    def get_session_date(self):
        """Extract session date from data or return current timestamp."""
        for df in [self.baseline_df, self.entrained_df]:
            try:
                clean_cols = [str(c).strip().lower() for c in df.columns]
                if 'date' in clean_cols:
                    date_col = df.columns[clean_cols.index('date')]
                    raw_date = str(df[date_col].iloc[0])
                    return raw_date.split('+')[0].strip()
            except Exception as e:
                logger.warning(f"Could not parse date from DataFrame: {e}")
                continue
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def preprocess_rr(self, rr):
        """
        IMPROVED: Physiological bounds + adaptive artifact detection (MAD).
        Preserves large resonant swings while catching true artifacts.
        """
        if len(rr) == 0: return np.array([])
        
        # Make sure it's float
        rr = np.array(rr, dtype=float)
        
        # 1. Unit Check
        if np.median(rr) < 10:
            rr = rr * 1000.0
            
        # 2. Physiological Bounds (300ms - 2000ms)
        # Keeps heart rates between 30 and 200 bpm
        rr = rr[(rr >= 300) & (rr <= 2000)]
        
        if len(rr) == 0: return np.array([])

        # 3. Adaptive Artifact Filter (MAD)
        # Median Absolute Deviation is robust against outliers
        median_rr = np.median(rr)
        mad = np.median(np.abs(rr - median_rr))
        
        # Keep beats within 5 MAD of median (very permissive for breathing swings)
        threshold = 5 * mad
        
        # Avoid filtering if MAD is 0 (perfectly stable rhythm)
        if mad > 0:
            clean_rr = rr[np.abs(rr - median_rr) <= threshold]
        else:
            clean_rr = rr
        
        # Fallback if too aggressive (removes > 20% of data)
        if len(clean_rr) < len(rr) * 0.8:
            logger.warning("MAD filter removed >20% of data. Using raw bounded data.")
            return rr
            
        return clean_rr

    def calculate_rmssd(self, rr):
        """Calculate Root Mean Square of Successive Differences (RMSSD)."""
        # Use cleaned data
        clean_rr = self.preprocess_rr(rr)
        if len(clean_rr) < 2: return 0
        diffs = np.diff(clean_rr)
        return np.sqrt(np.mean(diffs**2))

    def calculate_dfa_alpha1(self, rr, scale_min=4, scale_max=16):
        """Calculate DFA Alpha-1 (Short-term fluctuation analysis)."""
        # Use cleaned data for structure analysis
        rr = self.preprocess_rr(rr)
        
        if len(rr) == 0: return 0
        y = np.cumsum(rr - np.mean(rr))
        N = len(y)
        real_max = min(scale_max, N // 2)
        if real_max < scale_min: return 0
        
        scales = np.arange(scale_min, real_max + 1)
        fluctuations = []
        
        # STANDARD DFA: Non-overlapping windows (Whole File logic)
        for s in scales:
            n_segments = N // s
            rms = 0
            
            for i in range(n_segments):
                # Standard non-overlapping segments
                start = i * s
                end = start + s
                segment = y[start:end]
                
                x = np.arange(s)
                # Detrend (Order 1)
                coeff = np.polyfit(x, segment, 1)
                trend = np.polyval(coeff, x)
                rms += np.sum((segment - trend)**2)
            
            if n_segments > 0:
                # F(s)
                f_s = np.sqrt(rms / (n_segments * s))
                fluctuations.append(f_s)
            else:
                fluctuations.append(0)
        
        valid = np.array(fluctuations) > 0
        if sum(valid) < 2: return 0
        
        # Fit log-log
        log_scales = np.log10(scales[valid])
        log_fluc = np.log10(np.array(fluctuations)[valid])
        alpha1 = np.polyfit(log_scales, log_fluc, 1)[0]
        
        return alpha1

    def calculate_resp_rate(self, rr):
        """
        Estimates respiratory rate from HRV spectrum (EDR) using Numpy.
        Returns BPM (float).
        """
        rr = self.preprocess_rr(rr)
        if len(rr) < 10: return 0
        
        # Time axis in seconds
        t = np.cumsum(rr) / 1000.0
        t = t - t[0]
        duration = t[-1]
        
        # Interpolate to Uniform Grid (4Hz)
        fs = 4.0
        num_samples = int(duration * fs)
        if num_samples < 10: return 0
        steps = np.linspace(0, duration, num_samples)
        
        # Linear interpolation is sufficient for peak detection
        rr_interp = np.interp(steps, t, rr)
        
        # Detrend (remove DC component)
        rr_interp = rr_interp - np.mean(rr_interp)
        
        # Windowing (Hanning)
        window = np.hanning(len(rr_interp))
        signal_w = rr_interp * window
        
        # FFT
        fft_vals = np.abs(np.fft.rfft(signal_w))**2
        freqs = np.fft.rfftfreq(len(signal_w), d=1/fs)
        
        # Look for peak in physiological range: 0.05 Hz (3 BPM) to 0.5 Hz (30 BPM)
        mask = (freqs >= 0.05) & (freqs <= 0.5)
        valid_freqs = freqs[mask]
        valid_fft = fft_vals[mask]
        
        if len(valid_freqs) == 0: return 0
        
        peak_idx = np.argmax(valid_fft)
        peak_freq = valid_freqs[peak_idx]
        
        return round(peak_freq * 60, 1)

    def calculate_baseline_hr(self, baseline_rr):
        """Calculate mean baseline heart rate from RR intervals."""
        clean_rr = self.preprocess_rr(baseline_rr)
        if len(clean_rr) < 5:
            return None, None
        mean_rr = np.mean(clean_rr)
        if mean_rr <= 0:
            return None, None
        mean_hr = 60000 / mean_rr
        return round(mean_rr, 1), round(mean_hr, 1)

    def run(self):
        """Execute the full analysis pipeline."""
        base_rr = self.get_rr_values(self.baseline_df)
        entr_rr = self.get_rr_values(self.entrained_df)

        # Calculations now use internal preprocessing
        a_base = self.calculate_dfa_alpha1(base_rr)
        a_entr = self.calculate_dfa_alpha1(entr_rr)
        r_base = self.calculate_rmssd(base_rr)
        r_entr = self.calculate_rmssd(entr_rr)
        resp_rate = self.calculate_resp_rate(entr_rr)
        baseline_mean_rr, baseline_hr = self.calculate_baseline_hr(base_rr)

        responsiveness_index = a_entr / a_base if a_base > 0 else 0
        power = r_entr / r_base if r_base > 0 else 0

        # Pass the profile so classification uses its precomputed thresholds
        # (no CSV re-reads) and matches what view_session/get_history display.
        interp = get_interpretation(a_base, a_entr, r_base, r_entr,
                                    user_profile=get_or_create_user_profile('default'))

        # Explicitly free large numpy arrays
        del base_rr, entr_rr

        self.results = {
            'date': self.get_session_date(),
            'a_base': round(a_base, 2),
            'a_entr': round(a_entr, 2),
            'responsiveness_index': round(responsiveness_index, 2),
            'r_base': round(r_base, 1),
            'r_entr': round(r_entr, 1),
            'power': round(power, 2),
            'entrained_resp_rate': resp_rate,
            'interp': interp,
            'baseline_mean_rr': baseline_mean_rr,
            'baseline_hr': baseline_hr
        }
        return self.results

    @staticmethod
    def _zscore_color_directional(z):
        """
        Map a z-score to an RGB color for DIRECTIONAL metrics (RMSSD, responsiveness,
        gain), where higher is generally better.
          z = 0  -> green  (your normal)
          z < 0  -> amber -> red   (increasingly low FOR YOU)
          z > 0  -> teal  -> blue  (increasingly high FOR YOU)
        Saturates beyond +/-2 SD. Continuous: no thresholds, just interpretation.
        """
        zc = max(-2.0, min(2.0, z))
        if zc >= 0:
            t = zc / 2.0
            r = 0.20 + (0.10 - 0.20) * t
            g = 0.65 + (0.45 - 0.65) * t
            b = 0.32 + (0.82 - 0.32) * t
        else:
            t = -zc / 2.0
            r = 0.20 + (0.82 - 0.20) * t
            g = 0.65 + (0.18 - 0.65) * t
            b = 0.32 + (0.15 - 0.32) * t
        return (r, g, b)

    @staticmethod
    def _alpha_color_band_centered(alpha_val):
        """
        Map a baseline-Alpha value to color for the BAND-CENTERED metric, where
        BOTH extremes are departures (low = depletion, high = rigidity) and the
        Available zone (0.75-1.25) is the desirable middle.
          inside 0.75-1.25 -> green
          below 0.75       -> amber -> red    (depletion)
          above 1.25       -> muted violet    (rigidity)
        Distinct high-end hue so users don't read 'high Alpha' as 'good like high RMSSD'.
        """
        lo, hi = 0.75, 1.25
        if lo <= alpha_val <= hi:
            return (0.20, 0.65, 0.32)
        elif alpha_val < lo:
            t = min((lo - alpha_val) / lo, 1.0)
            r = 0.20 + (0.82 - 0.20) * t
            g = 0.65 + (0.30 - 0.65) * t
            b = 0.32 + (0.15 - 0.32) * t
            return (r, g, b)
        else:
            t = min((alpha_val - hi) / hi, 1.0)
            r = 0.20 + (0.55 - 0.20) * t
            g = 0.65 + (0.25 - 0.65) * t
            b = 0.32 + (0.70 - 0.32) * t
            return (r, g, b)

    def _draw_zscore_gradient(self, ax, x_center, y_max, mean, sd, width=0.5, n=256):
        """
        Paint a continuous vertical z-score gradient behind a directional bar.
        Green at the personal mean, fading to red below and blue above by +/-2 SD.
        Skipped (no-op) when sd is missing/zero — e.g. cold start — so the panel
        simply shows the bar with no misleading color field.
        """
        if not sd or sd <= 0:
            return
        ys = np.linspace(0, y_max, n)
        zs = (ys - mean) / sd
        colors = np.array([self._zscore_color_directional(z) for z in zs])
        grad = colors.reshape(n, 1, 3)
        ax.imshow(grad, extent=[x_center - width / 2, x_center + width / 2, 0, y_max],
                  origin='lower', aspect='auto', alpha=0.28, zorder=0)

    # Cache for the alpha gradient: it depends only on (y_max, n), both fixed
    # in practice, so build it once instead of 256 color calls per plot.
    _alpha_grad_cache = {}

    def _draw_alpha_gradient(self, ax, x_center, y_max, width=0.5, n=256):
        """
        Paint the band-centered Alpha gradient behind a baseline-Alpha bar:
        green through the Available zone, cautionary toward both tails.
        Uses fixed physiological zones (not personal stats), so it always renders.
        """
        key = (y_max, n)
        grad = self._alpha_grad_cache.get(key)
        if grad is None:
            ys = np.linspace(0, y_max, n)
            colors = np.array([self._alpha_color_band_centered(v) for v in ys])
            grad = colors.reshape(n, 1, 3)
            self._alpha_grad_cache[key] = grad
        ax.imshow(grad, extent=[x_center - width / 2, x_center + width / 2, 0, y_max],
                  origin='lower', aspect='auto', alpha=0.28, zorder=0)

    def plot(self, filename):
        """Generate and save the comparison plot with historical error bars."""
        fig, ax = plt.subplots(2, 2, figsize=(12, 10))
        base_rr = self.get_rr_values(self.baseline_df)
        entr_rr = self.get_rr_values(self.entrained_df)

        # Use cleaned data for plotting too, so graph matches metrics
        clean_b = self.preprocess_rr(base_rr)
        clean_e = self.preprocess_rr(entr_rr)

        bpm_b = 60000/clean_b if len(clean_b) > 0 else []
        bpm_e = 60000/clean_e if len(clean_e) > 0 else []

        # --- Top Left: Baseline Heart Rate ---
        ax[0,0].plot(bpm_b, color='gray', alpha=0.7)
        ax[0,0].set_title(f"Baseline Heart Rate", fontsize=12)
        ax[0,0].set_ylabel("BPM")
        ax[0,0].grid(True, alpha=0.3)
        
        # --- Top Right: Entrained Heart Rate ---
        ax[0,1].plot(bpm_e, color='#007acc', linewidth=2)
        ax[0,1].set_title(f"Entrained Heart Rate", fontsize=12)
        ax[0,1].grid(True, alpha=0.3)
        
        cats = ['Baseline', 'Entrained']
        x_pos = np.arange(len(cats))  # X positions for bars

        # --- Calculate Historical Stats (Mean +/- SD) ---
        # We read history, add current session, and compute stats
        hist_means = {'a_base': 0, 'a_entr': 0, 'r_base': 0, 'r_entr': 0}
        hist_stds = {'a_base': 0, 'a_entr': 0, 'r_base': 0, 'r_entr': 0}

        try:
            # 1. Load History
            if os.path.exists(HISTORY_FILE):
                df_hist = pd.read_csv(HISTORY_FILE, skipinitialspace=True)

                # Calculate stats directly without concatenation (more efficient)
                cols_map = {
                    'a_base': 'Baseline_Alpha',
                    'a_entr': 'Entrained_Alpha',
                    'r_base': 'Baseline_RMSSD',
                    'r_entr': 'Entrained_RMSSD'
                }

                for k, col in cols_map.items():
                    if col in df_hist.columns:
                        vals = pd.to_numeric(df_hist[col], errors='coerce').dropna()
                        if len(vals) > 0:
                            hist_means[k] = vals.mean()
                            sd = vals.std()
                            if pd.isna(sd): sd = 0
                            hist_stds[k] = sd

                del df_hist  # Explicitly free memory
        except Exception as e:
            logger.error(f"Error calculating stats for plot: {e}")

        # --- Bottom Left: ALPHA-1 Comparison (Structure) ---
        vals_alpha = [self.results['a_base'], self.results['a_entr']]
        alpha_ymax = 2.0
        error_offset = 0.3

        # Z-score gradient background (continuous interpretation, no thresholds):
        #  - Baseline Alpha is BAND-CENTERED: green in the Available zone (0.75-1.25),
        #    fading to caution at both tails (depletion low, rigidity high).
        #  - Entrained Alpha is DIRECTIONAL vs the user's own entrained history:
        #    green at their mean, red below, blue above.
        self._draw_alpha_gradient(ax[1, 0], x_pos[0], alpha_ymax, width=0.5)
        self._draw_zscore_gradient(ax[1, 0], x_pos[1], alpha_ymax,
                                   hist_means['a_entr'], hist_stds['a_entr'], width=0.5)

        # Plot Bars (semi-transparent so the gradient reads through)
        bars1 = ax[1, 0].bar(x_pos, vals_alpha, color=['#555555', '#1f4e79'],
                             width=0.5, alpha=0.55, zorder=2)
        ax[1, 0].bar_label(bars1, fmt='%.2f', padding=3, fontsize=12, fontweight='bold')

        # Plot personal mean markers (Mean ± 1 SD) on top
        ax[1, 0].errorbar(x_pos + error_offset, [hist_means['a_base'], hist_means['a_entr']],
                          yerr=[hist_stds['a_base'], hist_stds['a_entr']],
                          fmt='o', color='black', capsize=8, linewidth=1.5,
                          label='Your Avg ± 1 SD', zorder=10)

        ax[1, 0].set_xticks(x_pos)
        ax[1, 0].set_xticklabels(cats)
        ax[1, 0].set_ylim(0, alpha_ymax)
        ax[1, 0].set_title("Responsiveness (Alpha-1)", fontsize=14, fontweight='bold', pad=15)
        ax[1, 0].set_ylabel("DFA Alpha-1")
        ax[1, 0].grid(True, axis='y', linestyle='--', alpha=0.3)
        ax[1, 0].legend(loc='upper left', fontsize='small')

        # --- Bottom Right: RMSSD Comparison (Volume) ---
        vals_rmssd = [self.results['r_base'], self.results['r_entr']]
        max_r = max(vals_rmssd) if vals_rmssd else 50
        rmssd_ymax = max_r * 1.3

        # Both RMSSD bars are DIRECTIONAL (higher generally better), each scored
        # against its own history: baseline vs baseline mean, entrained vs entrained
        # mean. Green at the personal mean, red below, blue above (±2 SD saturating).
        self._draw_zscore_gradient(ax[1, 1], x_pos[0], rmssd_ymax,
                                   hist_means['r_base'], hist_stds['r_base'], width=0.5)
        self._draw_zscore_gradient(ax[1, 1], x_pos[1], rmssd_ymax,
                                   hist_means['r_entr'], hist_stds['r_entr'], width=0.5)

        # Plot Bars (semi-transparent so the gradient reads through)
        bars2 = ax[1, 1].bar(x_pos, vals_rmssd, color=['#555555', '#b5651d'],
                             width=0.5, alpha=0.55, zorder=2)
        ax[1, 1].bar_label(bars2, fmt='%.1f', padding=3, fontsize=12, fontweight='bold')

        # Plot personal mean markers (Mean ± 1 SD) on top
        ax[1, 1].errorbar(x_pos + error_offset, [hist_means['r_base'], hist_means['r_entr']],
                          yerr=[hist_stds['r_base'], hist_stds['r_entr']],
                          fmt='o', color='black', capsize=8, linewidth=1.5,
                          label='Your Avg ± 1 SD', zorder=10)

        ax[1, 1].set_xticks(x_pos)
        ax[1, 1].set_xticklabels(cats)
        ax[1, 1].set_ylim(0, rmssd_ymax)
        ax[1, 1].set_title("Power (RMSSD)", fontsize=14, fontweight='bold', pad=15)
        ax[1, 1].set_ylabel("RMSSD (ms)")
        ax[1, 1].grid(True, axis='y', linestyle='--', alpha=0.3)
        ax[1, 1].legend(loc='upper left', fontsize='small')

        plt.tight_layout()
        filepath = os.path.join(app.config['STATIC_FOLDER'], filename)
        plt.savefig(filepath)
        plt.close(fig)

        # Clear matplotlib caches to prevent memory accumulation
        plt.close('all')

        # Explicitly delete large arrays
        del base_rr, entr_rr, clean_b, clean_e, bpm_b, bpm_e

        return filename

def ensure_history_header():
    """Ensure history CSV file exists and has correct headers."""
    if not os.path.exists(HISTORY_FILE):
        return

    # UPDATED: Schema Migration Logic
    # Reads file, checks for missing columns, adds them if needed
    try:
        df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]

        changed = False
        renames = {old: new for old, new in LEGACY_COLUMN_RENAMES.items()
                   if old in df.columns and new not in df.columns}
        if renames:
            df.rename(columns=renames, inplace=True)
            changed = True

        for col in HISTORY_COLUMNS:
            if col not in df.columns:
                df[col] = None # Add missing column
                changed = True
        
        if changed:
            # Schema rewrites are rare and destructive if buggy (a bad migration
            # once wiped two columns) — keep a timestamped copy of the original.
            backup = f"{HISTORY_FILE}.schema-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            shutil.copy2(HISTORY_FILE, backup)
            df[HISTORY_COLUMNS].to_csv(HISTORY_FILE, index=False)
            logger.info(f"Updated history file schema with new columns (backup: {backup}).")
            
    except Exception as e:
        logger.error(f"Error repairing history header: {e}")

def save_to_history(m, plot_file):
    """Save analysis metrics to history CSV."""
    ensure_history_header()
    date_str = str(m['date']).strip()

    # Duplicate check + removal in a single CSV read (was two).
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
            if 'Date' in df.columns:
                dates = df['Date'].astype(str).str.strip()
                if (dates == date_str).any():
                    df[dates != date_str].to_csv(HISTORY_FILE, index=False)
                    logger.info(f"Updated entry for: {date_str}")
            del df
        except Exception as e:
            logger.error(f"Error checking/removing duplicate history entry: {e}")

    with open(HISTORY_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            date_str,
            m['a_base'],
            m['a_entr'],
            m['responsiveness_index'],
            m['r_base'],
            m['r_entr'],
            m['power'],
            m.get('entrained_resp_rate', 0),
            plot_file,
            m.get('baseline_hr', ''),
            m.get('baseline_mean_rr', '')
        ])

    # Phase 2: Update user profile after session is saved.
    # session_count is set inside update_user_profile() from the history
    # DataFrame it already loads, so no extra CSV read is needed here.
    try:
        update_user_profile('default')
        logger.info("Updated user profile after session save.")
    except Exception as e:
        logger.warning(f"Could not update user profile: {e}")

def get_history():
    """Retrieve all history records from CSV with in-memory caching.

    Only re-reads the CSV file if it has been modified since the last load,
    reducing memory thrashing from repeated DataFrame allocations.
    """
    global _history_cache

    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        # Check if file has been modified since last load
        current_mtime = os.path.getmtime(HISTORY_FILE)
        if _history_cache['data'] is not None and _history_cache['mtime'] == current_mtime:
            return _history_cache['data']

        ensure_history_header()
        df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]

        df.rename(columns=LEGACY_COLUMN_RENAMES, inplace=True)

        if df.empty:
            del df
            gc.collect()
            _history_cache['data'] = []
            _history_cache['mtime'] = current_mtime
            return []

        # Load the user profile once. Passing it into get_interpretation() lets
        # every row reuse the profile's precomputed ceiling/responsiveness thresholds
        # instead of re-reading and re-percentiling the history CSV per record
        # (previously ~2 CSV parses per row on every page load).
        profile = get_or_create_user_profile('default')

        # Resolve depleted-floor stats once for ALL rows. If the stored profile
        # lacks them (e.g. stale user_profiles.json from before these fields
        # existed), compute from the already-loaded df here rather than letting
        # get_interpretation() re-read the CSV once per row. Must run before
        # the descending date sort so tail() still means "most recent".
        if not (profile.get('baseline_rmssd_mean') and profile.get('baseline_rmssd_sd')):
            f_mean, f_sd = compute_baseline_rmssd_stats(HISTORY_FILE, CEILING_WINDOW_SESSIONS, df=df)
            if f_mean is not None:
                profile = dict(profile)  # copy: don't mutate the saved profile
                profile['baseline_rmssd_mean'] = f_mean
                profile['baseline_rmssd_sd'] = f_sd

        if 'Date' in df.columns:
            df['_sort_date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='_sort_date', ascending=False)
            df = df.drop(columns=['_sort_date'])

        records = df.to_dict('records')
        del df

        for r in records:
            try:
                a_base = float(r.get('Baseline_Alpha', 0))
                a_entr = float(r.get('Entrained_Alpha', 0))
                r_base = float(r.get('Baseline_RMSSD', 0))
                r_entr = float(r.get('Entrained_RMSSD', 0))
            except (ValueError, TypeError):
                a_base, a_entr, r_base, r_entr = 0, 0, 0, 0

            # Ensure resp rate exists for older records
            if 'Entrained_Resp_Rate' not in r or pd.isna(r['Entrained_Resp_Rate']):
                r['Entrained_Resp_Rate'] = '-'

            interp = get_interpretation(a_base, a_entr, r_base, r_entr, user_profile=profile)
            r['color'] = interp['color']
            r['state'] = interp['state']
            r['goal'] = interp['goal']

        # Cache the results
        _history_cache['data'] = records
        _history_cache['mtime'] = current_mtime
        gc.collect()
        return records

    except Exception as e:
        logger.error(f"Error reading history: {e}")
        return []

def delete_from_history(date_str):
    """Delete a record and its plot file from history."""
    if not os.path.exists(HISTORY_FILE):
        return

    try:
        df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
        
        to_delete = df[df['Date'].astype(str).str.strip() == date_str]
        
        for plot_file in to_delete['Plot_File'].dropna():
             if isinstance(plot_file, str) and plot_file.endswith('.png'):
                 plot_path = os.path.join(app.config['STATIC_FOLDER'], plot_file)
                 if os.path.exists(plot_path):
                     try:
                         os.remove(plot_path)
                         logger.info(f"Deleted plot file: {plot_file}")
                     except Exception as ex:
                         logger.error(f"Error deleting plot file {plot_file}: {ex}")

        df_new = df[df['Date'].astype(str).str.strip() != date_str]
        df_new.to_csv(HISTORY_FILE, index=False)
        logger.info(f"Deleted session(s) with date: {date_str}")
        
    except Exception as e:
        logger.error(f"Error during deletion: {e}")

def allowed_file(filename):
    """Check if the file has an allowed extension (csv or txt)."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv', 'txt'}

def process_files(f1, f2):
    """
    Process uploaded files with robust error handling and cleanup.
    
    Args:
        f1 (FileStorage): Baseline file object.
        f2 (FileStorage): Entrained file object.
        
    Returns:
        tuple: (metrics dict, analyzer instance) or (None, None) if error.
    """
    # Secure filenames. secure_filename() can return '' for names made up
    # entirely of unsafe characters; fall back to a unique name so the two
    # uploads never collide on an empty path.
    filename1 = secure_filename(f1.filename) or f"baseline_{uuid.uuid4().hex}.csv"
    filename2 = secure_filename(f2.filename) or f"entrained_{uuid.uuid4().hex}.csv"
    
    p1 = os.path.join(app.config['UPLOAD_FOLDER'], filename1)
    p2 = os.path.join(app.config['UPLOAD_FOLDER'], filename2)

    # 1. Save Baseline
    try:
        f1.save(p1)
        logger.info(f"Saved baseline file: {p1}")
    except Exception as e:
        logger.error(f"Error saving baseline file: {e}")
        return None, None

    # 2. Save Entrained (with cleanup if failure)
    try:
        f2.save(p2)
        logger.info(f"Saved entrained file: {p2}")
    except Exception as e:
        logger.error(f"Error saving entrained file: {e}")
        # Cleanup first file if second fails to avoid orphans
        if os.path.exists(p1):
            os.remove(p1)
            logger.info(f"Cleaned up baseline file due to error: {p1}")
        return None, None

    # 3. Analyze
    try:
        analyzer = AutonomicFlexibilityAnalyzer(p1, p2)
        metrics = analyzer.run()

        # Validate that we actually got numbers back
        if not metrics or 'responsiveness_index' not in metrics:
            raise ValueError("Analysis failed to generate valid metrics.")

        # 4. Rename and preserve uploaded files for future reference
        try:
            session_date = metrics['date']
            # Parse date: "2026-06-08 17:28:18" -> date "2026-6-8", hour 17
            date_time_parts = session_date.split()
            date_parts = date_time_parts[0].split('-')
            if len(date_parts) == 3:
                year, month, day = date_parts
                date_str = f"{year}-{int(month)}-{int(day)}"
            else:
                date_str = session_date.split()[0]

            # Extract hour and minute, convert to time hint (8a, 10a15, 5p30, etc.)
            time_hint = ''
            if len(date_time_parts) > 1:
                try:
                    time_parts = date_time_parts[1].split(':')
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0

                    # Convert to 12-hour format with am/pm
                    if hour == 0:
                        hour_12 = 12
                        ampm = 'a'
                    elif hour < 12:
                        hour_12 = hour
                        ampm = 'a'
                    elif hour == 12:
                        hour_12 = 12
                        ampm = 'p'
                    else:
                        hour_12 = hour - 12
                        ampm = 'p'

                    # Only add minutes if non-zero
                    if minute > 0:
                        time_hint = f'{hour_12}{ampm}{minute:02d}'
                    else:
                        time_hint = f'{hour_12}{ampm}'
                except (ValueError, IndexError):
                    pass

            # Rename files with time hint: 2026-6-8_RR_baseline 5p.csv
            suffix = f" {time_hint}" if time_hint else ""
            new_p1 = os.path.join(app.config['UPLOAD_FOLDER'], f"{date_str}_RR_baseline{suffix}.csv")
            new_p2 = os.path.join(app.config['UPLOAD_FOLDER'], f"{date_str}_RR_entrained{suffix}.csv")

            if os.path.exists(p1):
                os.rename(p1, new_p1)
                logger.info(f"Saved baseline RR file: {new_p1}")
            if os.path.exists(p2):
                os.rename(p2, new_p2)
                logger.info(f"Saved entrained RR file: {new_p2}")
        except Exception as e:
            logger.warning(f"Could not rename/preserve RR files: {e}")
            # Don't fail the whole process if file preservation fails

        return metrics, analyzer
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        # Clean up temp files on error
        for path in (p1, p2):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    """Handle the main page request."""
    if request.method == 'POST':
        # Check if files are present in request
        if 'baseline' not in request.files or 'entrained' not in request.files:
            return "Missing files", 400

        f1 = request.files['baseline']
        f2 = request.files['entrained']

        # Check if filenames are empty
        if f1.filename == '' or f2.filename == '':
            return "No selected file", 400

        if f1 and allowed_file(f1.filename) and f2 and allowed_file(f2.filename):
            metrics, analyzer = process_files(f1, f2)

            if metrics and analyzer:
                try:
                    img_name = f"plot_{uuid.uuid4().hex}.png"
                    analyzer.plot(img_name)

                    session_date = metrics['date']
                    save_to_history(metrics, img_name)

                    # Explicitly free the analyzer object
                    del analyzer, metrics
                    gc.collect()

                    return redirect(url_for('view_session', date=session_date))
                except Exception as e:
                    logger.error(f"Error saving results/plotting: {e}")
                    return "Error generating results", 500
            else:
                return "Error processing files. Please ensure they are valid CSVs.", 400
        else:
            return "Invalid file type. Please upload .csv files.", 400

    history = get_history()
    return render_template('index.html', history=history)

@app.route('/session')
def view_session():
    """Handle the session page request."""
    date_str = request.args.get('date')
    history = get_history()
    
    target = next((r for r in history if str(r['Date']) == date_str), None)
    
    if not target:
        if history:
            target = history[0]
        else:
            return redirect(url_for('index'))

    def to_num(val):
        try: return float(val)
        except (ValueError, TypeError): return 0

    metrics = {
        'date': target['Date'],
        'a_base': to_num(target.get('Baseline_Alpha', 0)),
        'a_entr': to_num(target.get('Entrained_Alpha', 0)),
        'responsiveness_index': to_num(target.get('Responsiveness_Index', 0)),
        'r_base': to_num(target.get('Baseline_RMSSD', 0)),
        'r_entr': to_num(target.get('Entrained_RMSSD', 0)),
        'power': to_num(target.get('Power', 0)),
        'entrained_resp_rate': target.get('Entrained_Resp_Rate', '-')
    }
    
    metrics['interp'] = get_interpretation(
        metrics['a_base'],
        metrics['a_entr'],
        metrics['r_base'],
        metrics['r_entr'],
        user_profile=get_or_create_user_profile('default')
    )
    
    plot_file = target.get('Plot_File')
    if plot_file == '-' or pd.isna(plot_file): plot_file = None
    
    return render_template('result.html', m=metrics, plot=plot_file, history=history)

@app.route('/latest')
def latest():
    """Redirect to the latest session."""
    history = get_history()
    if history:
        return redirect(url_for('view_session', date=history[0]['Date']))
    return redirect(url_for('index'))

@app.route('/delete', methods=['POST'])
def delete():
    """Handle session deletion."""
    date_str = request.form.get('date')
    if date_str:
        delete_from_history(date_str)
    return redirect(url_for('index'))

@app.route('/health')
def health():
    """Liveness check for the container health probe. Deliberately does not
    touch history or templates so a data bug can't mark the app unhealthy."""
    return "ok"

@app.route('/debug')
def debug():
    """Debug endpoint to view history file content."""
    if not os.path.exists(HISTORY_FILE):
        return "No history file found."
    with open(HISTORY_FILE, 'r') as f:
        content = f.read()
    return Response(content, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
