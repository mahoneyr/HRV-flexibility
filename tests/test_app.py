"""Tests for the two highest-risk areas: the state classifier and the
history CSV schema migration (a bad migration once wiped two columns).

Run inside the app container so pandas/numpy match production:
    docker exec -w /app hrv_flexibility_app python -m pytest tests -q
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as hrv

# Synthetic profile so get_interpretation() never falls back to reading the
# history CSV. Values are illustrative, chosen to make case boundaries obvious:
# ceiling 40.0, tiebreaker 2.4, floor mean/sd 20.0/5.0 (z=-2 at b_rmssd=10.0).
PROFILE = {
    'rmssd_ceiling_computed': 40.0,
    'responsiveness_threshold_computed': 2.4,
    'baseline_rmssd_mean': 20.0,
    'baseline_rmssd_sd': 5.0,
}

STATE_KEYS = [
    'running_on_fumes', 'surfing_the_wave', 'laser_focus', 'tug_of_war',
    'attentive', 'stuck', 'relying_on_reserves', 'running_low',
    'fragile_calm', 'feeling_the_flow', 'burned_out', 'unknown',
]


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    # Never let a test near the real history file.
    monkeypatch.setattr(hrv, 'HISTORY_FILE', str(tmp_path / 'history.csv'))
    # Assert on state keys, decoupled from the prose in states.json.
    monkeypatch.setattr(hrv, 'STATE_DEFINITIONS',
                        {k: {'state': k, 'color': 'x', 'goal': ''} for k in STATE_KEYS})


def classify(b_alpha, e_alpha, b_rmssd, e_rmssd):
    return hrv.get_interpretation(b_alpha, e_alpha, b_rmssd, e_rmssd,
                                  user_profile=PROFILE)['state']


# (b_alpha, e_alpha, b_rmssd, e_rmssd) -> expected state key.
# Thresholds in play: RESPONSIVENESS_THRESHOLD=1.2, POWER_THRESHOLD=1.5,
# POWER_MARGIN_PCT=0.90 (near-miss floor 1.35), tier bounds 0.75/1.25.
CLASSIFIER_CASES = [
    # Overrides (checked before the tier matrix)
    ((1.0, 1.3, 9.0, 20.0), 'running_on_fumes'),    # depleted floor: z = -2.2
    ((1.0, 1.3, 41.0, 48.0), 'surfing_the_wave'),   # baseline >= personal ceiling (40)
    # Tier III: high baseline (b_alpha > 1.25)
    ((1.3, 1.60, 20.0, 32.0), 'laser_focus'),       # resp 1.23, power 1.6
    ((1.3, 1.40, 20.0, 32.0), 'tug_of_war'),        # resp 1.08 below threshold
    ((1.3, 1.60, 20.0, 24.0), 'attentive'),         # power 1.2 below threshold
    ((1.3, 1.35, 20.0, 20.0), 'stuck'),             # neither axis responds
    # Tier I: low baseline (b_alpha < 0.75)
    ((0.7, 0.90, 20.0, 32.0), 'relying_on_reserves'),
    ((0.7, 0.75, 20.0, 32.0), 'running_low'),
    ((0.5, 1.25, 20.0, 28.0), 'relying_on_reserves'),  # tiebreaker rescue: resp 2.5, power 1.4
    ((0.5, 0.70, 20.0, 22.0), 'fragile_calm'),         # power 1.1 misses the 1.35 rescue floor
    ((0.7, 0.70, 20.0, 20.0), 'running_on_fumes'),
    # Tier II: available baseline (0.75 <= b_alpha <= 1.25)
    ((1.0, 1.30, 20.0, 32.0), 'feeling_the_flow'),
    ((1.0, 1.10, 20.0, 32.0), 'tug_of_war'),
    ((1.0, 2.50, 20.0, 28.0), 'feeling_the_flow'),     # tiebreaker rescue
    ((1.0, 1.30, 20.0, 24.0), 'fragile_calm'),
    ((1.0, 1.00, 20.0, 20.0), 'burned_out'),
]


@pytest.mark.parametrize('inputs,expected', CLASSIFIER_CASES)
def test_classifier(inputs, expected):
    assert classify(*inputs) == expected


def test_classifier_survives_zero_inputs():
    # Safety clamps must prevent division errors; exact state doesn't matter.
    assert classify(0, 0, 0, 0) in STATE_KEYS


def test_depleted_floor_disarmed_without_norms():
    # Same severe baseline as the depleted-floor case, but a cold-start profile
    # (no mean/sd) must not fire the override. With power 2.22 and resp 1.3 the
    # tier-II matrix classifies it as a full response instead.
    profile = dict(PROFILE, baseline_rmssd_mean=None, baseline_rmssd_sd=None)
    state = hrv.get_interpretation(1.0, 1.3, 9.0, 20.0, user_profile=profile)['state']
    assert state == 'feeling_the_flow'


# --- Schema migration -------------------------------------------------------

# Synthetic rows in the pre-rename schema. Values are made up; only the
# column names matter to these tests.
LEGACY_ROWS = {
    'Date': ['2020-01-01 08:00:00', '2020-01-02 08:00:00'],
    'Baseline_Alpha': [1.00, 1.10],
    'Entrained_Alpha': [1.50, 1.40],
    'Coherence_Index': [1.50, 1.27],
    'Baseline_RMSSD': [20.0, 25.0],
    'Entrained_RMSSD': [30.0, 35.0],
    'Vagal_Gain': [1.50, 1.40],
    'Entrained_Resp_Rate': [5.5, 5.5],
    'Plot_File': ['a.png', 'b.png'],
    'Baseline_HR': [70.0, 65.0],
    'Baseline_Mean_RR': [857.0, 923.0],
}


def history_path(tmp_path):
    return tmp_path / 'history.csv'


def test_migration_renames_legacy_columns_preserving_values(tmp_path):
    p = history_path(tmp_path)
    pd.DataFrame(LEGACY_ROWS).to_csv(p, index=False)

    hrv.ensure_history_header()

    df = pd.read_csv(p)
    assert list(df.columns) == hrv.HISTORY_COLUMNS
    assert 'Coherence_Index' not in df.columns and 'Vagal_Gain' not in df.columns
    # The whole point: renamed columns keep their historical values.
    assert df['Responsiveness_Index'].tolist() == LEGACY_ROWS['Coherence_Index']
    assert df['Power'].tolist() == LEGACY_ROWS['Vagal_Gain']
    assert df['Baseline_RMSSD'].tolist() == LEGACY_ROWS['Baseline_RMSSD']


def test_migration_handles_oldest_schema(tmp_path):
    p = history_path(tmp_path)
    pd.DataFrame({
        'Date': ['2020-01-01 08:00:00'],
        'Normal_Alpha': [1.00],
        'Entrained_Alpha': [1.50],
        'ratio': [1.50],
        'Normal_RMSSD': [20.0],
        'Entrained_RMSSD': [30.0],
    }).to_csv(p, index=False)

    hrv.ensure_history_header()

    df = pd.read_csv(p)
    assert list(df.columns) == hrv.HISTORY_COLUMNS
    assert df['Baseline_Alpha'].tolist() == [1.00]
    assert df['Responsiveness_Index'].tolist() == [1.50]
    # Columns the old schema never had are added, empty.
    assert df['Power'].isna().all()


def test_migration_backs_up_before_rewriting(tmp_path):
    p = history_path(tmp_path)
    pd.DataFrame(LEGACY_ROWS).to_csv(p, index=False)

    hrv.ensure_history_header()

    backups = list(tmp_path.glob('history.csv.schema-backup-*'))
    assert len(backups) == 1
    original = pd.read_csv(backups[0])
    assert original['Vagal_Gain'].tolist() == LEGACY_ROWS['Vagal_Gain']


def test_migration_leaves_current_schema_untouched(tmp_path):
    p = history_path(tmp_path)
    df_in = pd.DataFrame({col: [1] for col in hrv.HISTORY_COLUMNS})
    df_in.to_csv(p, index=False)
    before = p.read_text()

    hrv.ensure_history_header()

    assert p.read_text() == before
    assert list(tmp_path.glob('history.csv.schema-backup-*')) == []
