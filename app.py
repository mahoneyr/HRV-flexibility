import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import uuid
import csv
import logging
import json
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
    'Baseline_Alpha', 'Entrained_Alpha', 'Coherence_Index', 
    'Baseline_RMSSD', 'Entrained_RMSSD', 'Vagal_Gain', 
    'Entrained_Resp_Rate',
    'Plot_File'
]

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

# --- 12-STATE "INTEGRATION & DYNAMICS" LOGIC (v2) ---
# Classification is based on a 2x2 response matrix (Coherence Ratio x Vagal Gain)
# with Tier context (Baseline Alpha) modifying the meaning of each cell.
# Entrained Alpha is now a reported output only — not a classifier.
#
# 2x2 Core:
#   Gain > 1.5 + Ratio > 1.2  →  Full Response  (Flow / Reserves / Laser)
#   Gain > 1.5 + Ratio < 1.2  →  Vagal Brake    (energy without organization)
#   Gain < 1.5 + Ratio > 1.2  →  Fragile Calm   (structure without amplitude)
#   Gain < 1.5 + Ratio < 1.2  →  No Response    (Burned Out / Stuck / Fumes)
#
# Special Override (applied first):
#   b_rmssd > 30 + Ratio > 1.2 →  Vagal Wave    (ceiling effect)

def get_interpretation(b_alpha, e_alpha, b_rmssd, e_rmssd):
    """
    Classifies user state using the 2x2 Response Matrix + Tier context framework.
    
    Args:
        b_alpha (float): Baseline DFA Alpha-1
        e_alpha (float): Entrained DFA Alpha-1 (reported only, not used for classification)
        b_rmssd (float): Baseline RMSSD
        e_rmssd (float): Entrained RMSSD
        
    Returns:
        dict: Dictionary containing state name, physiology, implication, goal, and color.
    """
    # Safety zeros to prevent division errors
    b_alpha = max(b_alpha, 0.001)
    b_rmssd = max(b_rmssd, 0.001)
    
    coherence_ratio = e_alpha / b_alpha
    vagal_gain = e_rmssd / b_rmssd
    
    # Identify the key based on logic
    key = "unknown"

    # --- SPECIAL OVERRIDE: VAGAL WAVE ---
    # High baseline RMSSD compresses relative gain — ceiling effect, not failure.
    if b_rmssd > 30 and coherence_ratio >= 1.2:
        key = "surfing_the_wave"

    # --- TIER III: HIGH BASELINE (b_alpha > 1.25) ---
    elif b_alpha > 1.25:
        if vagal_gain >= 1.5 and coherence_ratio >= 1.2:
            key = "laser_focus"          # Full response from high base
        elif vagal_gain >= 1.5 and coherence_ratio < 1.2:
            key = "tug_of_war"           # Vagal Brake — energy without structure
        elif vagal_gain < 1.5 and coherence_ratio >= 1.2:
            key = "attentive"            # Structure held, no vagal recruitment
        else:
            key = "stuck"                # No response in either axis

    # --- TIER I: LOW BASELINE (b_alpha < 0.75) ---
    elif b_alpha < 0.75:
        if vagal_gain >= 1.5 and coherence_ratio >= 1.2:
            key = "relying_on_reserves"  # Full response despite low base
        elif vagal_gain >= 1.5 and coherence_ratio < 1.2:
            key = "running_low"          # Vagal Brake on depleted system
        elif vagal_gain < 1.5 and coherence_ratio >= 1.2:
            key = "fragile_calm"         # Structure shifted, amplitude limited
        else:
            key = "running_on_fumes"     # No response — system is depleted

    # --- TIER II: AVAILABLE BASELINE (0.75 <= b_alpha <= 1.25) ---
    else:
        if vagal_gain >= 1.5 and coherence_ratio >= 1.2:
            key = "feeling_the_flow"     # Full response — optimal state
        elif vagal_gain >= 1.5 and coherence_ratio < 1.2:
            key = "tug_of_war"           # Vagal Brake — energy without structure
        elif vagal_gain < 1.5 and coherence_ratio >= 1.2:
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
        "vagal_gain": f"{vagal_gain:.2f}",
        "coherence_ratio": f"{coherence_ratio:.2f}",
        "b_rmssd": f"{b_rmssd:.1f}",
        "e_rmssd": f"{e_rmssd:.1f}"
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
            except:
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
        
        coherence_index = a_entr / a_base if a_base > 0 else 0
        vagal_gain = r_entr / r_base if r_base > 0 else 0
        
        interp = get_interpretation(a_base, a_entr, r_base, r_entr)
        
        self.results = {
            'date': self.get_session_date(),
            'a_base': round(a_base, 2), 
            'a_entr': round(a_entr, 2),
            'coherence_index': round(coherence_index, 2),
            'r_base': round(r_base, 1), 
            'r_entr': round(r_entr, 1),
            'vagal_gain': round(vagal_gain, 2),
            'entrained_resp_rate': resp_rate,
            'interp': interp 
        }
        return self.results

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
            df_hist = pd.DataFrame()
            if os.path.exists(HISTORY_FILE):
                df_hist = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
            
            # 2. Add Current Session (in memory) for the sake of stats
            current_data = {
                'Baseline_Alpha': self.results.get('a_base'),
                'Entrained_Alpha': self.results.get('a_entr'),
                'Baseline_RMSSD': self.results.get('r_base'),
                'Entrained_RMSSD': self.results.get('r_entr')
            }
            # Append current row using concat
            df_hist = pd.concat([df_hist, pd.DataFrame([current_data])], ignore_index=True)
            
            # 3. Calculate Stats
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
                        # Use Sample SD (ddof=1) or Population (ddof=0). Default is 1.
                        # If len=1, std is NaN, so handle that.
                        sd = vals.std()
                        if pd.isna(sd): sd = 0
                        hist_stds[k] = sd
        except Exception as e:
            logger.error(f"Error calculating stats for plot: {e}")

        # --- Bottom Left: ALPHA-1 Comparison (Structure) ---
        vals_alpha = [self.results['a_base'], self.results['a_entr']]
        colors_alpha = ['gray', '#007acc'] 
        
        # Plot Bars
        bars1 = ax[1, 0].bar(x_pos, vals_alpha, color=colors_alpha, width=0.5)
        ax[1, 0].bar_label(bars1, fmt='%.2f', padding=3, fontsize=12, fontweight='bold')
        
        # Plot Error Bars (Offset to the right)
        error_offset = 0.3
        ax[1, 0].errorbar(x_pos + error_offset, [hist_means['a_base'], hist_means['a_entr']], 
                          yerr=[hist_stds['a_base'], hist_stds['a_entr']],
                          fmt='o', color='black', capsize=8, linewidth=1.5,
                          label='Avg ± 1 SD (History)', zorder=10)

        # Set X-Ticks
        ax[1, 0].set_xticks(x_pos)
        ax[1, 0].set_xticklabels(cats)

        ax[1, 0].axhspan(0.75, 1.25, color='gray', alpha=0.1, label='Resting Norm', zorder=0)
        ax[1, 0].axhspan(1.35, 1.6, color='#007acc', alpha=0.1, label='Coherence Target', zorder=0)
        ax[1, 0].set_ylim(0, 2.0)
        ax[1, 0].set_title("Coherence (Alpha-1)", fontsize=14, fontweight='bold', pad=15)
        ax[1, 0].set_ylabel("DFA Alpha-1")
        ax[1, 0].grid(True, axis='y', linestyle='--', alpha=0.5)
        ax[1, 0].legend(loc='upper left', fontsize='small')

        # --- Bottom Right: RMSSD Comparison (Volume) ---
        vals_rmssd = [self.results['r_base'], self.results['r_entr']]
        colors_rmssd = ['gray', '#ff7f0e'] 
        
        # Plot Bars
        bars2 = ax[1, 1].bar(x_pos, vals_rmssd, color=colors_rmssd, width=0.5)
        ax[1, 1].bar_label(bars2, fmt='%.1f', padding=3, fontsize=12, fontweight='bold')
        
        # Plot Error Bars (Offset to the right)
        ax[1, 1].errorbar(x_pos + error_offset, [hist_means['r_base'], hist_means['r_entr']],
                          yerr=[hist_stds['r_base'], hist_stds['r_entr']],
                          fmt='o', color='black', capsize=8, linewidth=1.5,
                          label='Avg ± 1 SD (History)', zorder=10)

        # Set X-Ticks
        ax[1, 1].set_xticks(x_pos)
        ax[1, 1].set_xticklabels(cats)

        max_r = max(vals_rmssd) if vals_rmssd else 50
        ax[1, 1].set_ylim(0, max_r * 1.3)
        ax[1, 1].set_title("Vagal Gain (RMSSD)", fontsize=14, fontweight='bold', pad=15)
        ax[1, 1].set_ylabel("RMSSD (ms)")
        ax[1, 1].grid(True, axis='y', linestyle='--', alpha=0.5)
        ax[1, 1].legend(loc='upper left', fontsize='small')

        plt.tight_layout()
        filepath = os.path.join(app.config['STATIC_FOLDER'], filename)
        plt.savefig(filepath)
        plt.close(fig)
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
        for col in HISTORY_COLUMNS:
            if col not in df.columns:
                df[col] = None # Add missing column
                changed = True
        
        if changed:
            df[HISTORY_COLUMNS].to_csv(HISTORY_FILE, index=False)
            logger.info("Updated history file schema with new columns.")
            
    except Exception as e:
        logger.error(f"Error repairing history header: {e}")

def save_to_history(m, plot_file):
    """Save analysis metrics to history CSV."""
    ensure_history_header()
    date_str = str(m['date']).strip()
    existing_dates = set()
    
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
            if 'Date' in df.columns:
                existing_dates = set(df['Date'].astype(str).str.strip().values)
        except:
            pass

    if date_str in existing_dates:
        try:
            df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
            df = df[df['Date'].astype(str).str.strip() != date_str]
            df.to_csv(HISTORY_FILE, index=False)
            logger.info(f"Updated entry for: {date_str}")
        except:
            pass

    with open(HISTORY_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            date_str, 
            m['a_base'], 
            m['a_entr'], 
            m['coherence_index'],
            m['r_base'], 
            m['r_entr'], 
            m['vagal_gain'], 
            m.get('entrained_resp_rate', 0), # New Field
            plot_file
        ])

def get_history():
    """Retrieve all history records from CSV."""
    if not os.path.exists(HISTORY_FILE): 
        return []

    try:
        ensure_history_header()
        df = pd.read_csv(HISTORY_FILE, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        
        rename_map = {
            'Normal_Alpha': 'Baseline_Alpha',
            'Normal_RMSSD': 'Baseline_RMSSD',
            'ratio': 'Coherence_Index'
        }
        df.rename(columns=rename_map, inplace=True)

        if df.empty: return []

        if 'Date' in df.columns:
            df['_sort_date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values(by='_sort_date', ascending=False)
            df = df.drop(columns=['_sort_date'])

        records = df.to_dict('records')
        
        for r in records:
            try:
                a_base = float(r.get('Baseline_Alpha', 0))
                a_entr = float(r.get('Entrained_Alpha', 0))
                r_base = float(r.get('Baseline_RMSSD', 0))
                r_entr = float(r.get('Entrained_RMSSD', 0))
            except:
                a_base, a_entr, r_base, r_entr = 0, 0, 0, 0
            
            # Ensure resp rate exists for older records
            if 'Entrained_Resp_Rate' not in r or pd.isna(r['Entrained_Resp_Rate']):
                r['Entrained_Resp_Rate'] = '-'
                
            interp = get_interpretation(a_base, a_entr, r_base, r_entr)
            r['color'] = interp['color']
            r['state'] = interp['state']
            r['goal'] = interp['goal'] 
            
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
    # Secure filenames
    filename1 = secure_filename(f1.filename)
    filename2 = secure_filename(f2.filename)
    
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
        if not metrics or 'coherence_index' not in metrics:
            raise ValueError("Analysis failed to generate valid metrics.")
            
        return metrics, analyzer
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
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
                    
                    save_to_history(metrics, img_name)
                    return redirect(url_for('view_session', date=metrics['date']))
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
        except: return 0

    metrics = {
        'date': target['Date'],
        'a_base': to_num(target.get('Baseline_Alpha', 0)),
        'a_entr': to_num(target.get('Entrained_Alpha', 0)),
        'coherence_index': to_num(target.get('Coherence_Index', 0)),
        'r_base': to_num(target.get('Baseline_RMSSD', 0)),
        'r_entr': to_num(target.get('Entrained_RMSSD', 0)),
        'vagal_gain': to_num(target.get('Vagal_Gain', 0)),
        'entrained_resp_rate': target.get('Entrained_Resp_Rate', '-')
    }
    
    metrics['interp'] = get_interpretation(
        metrics['a_base'], 
        metrics['a_entr'], 
        metrics['r_base'],
        metrics['r_entr']
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

@app.route('/delete')
def delete():
    """Handle session deletion."""
    date_str = request.args.get('date')
    if date_str:
        delete_from_history(date_str)
    return redirect(url_for('index'))

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
