"""
Central configuration for Module 2 (Risk + Health + Link Analyzer).

Everything tunable lives here so you can adjust behaviour during the
hackathon without hunting through logic files. These DEFAULT_* baselines
are the fallback used when no operator/machine history is supplied, so
the module always runs standalone.
"""

# ---------------------------------------------------------------------------
# Fallback baselines — used when POST /analyze receives no history array.
# Represent a "healthy, normal" operator + machine. Numbers are illustrative
# and match Module 1's simulated ranges.
# ---------------------------------------------------------------------------
DEFAULT_OPERATOR_BASELINE = {
    "idle_minutes": 14.0,       # a normal shift's typical idle
    "load_cycles_per_hour": 2.0,  # normal harsh/high-load cycle rate
}

DEFAULT_MACHINE_BASELINE = {
    "hydraulic_pressure": 180.0,  # bar-ish, simulated
    "vibration": 0.35,            # simulated unit
    "engine_temp": 90.0,          # deg C
    "oil_pressure": 4.2,          # bar
    "hydraulic_temp": 70.0,       # deg C
    "rpm": 1800.0,
}

# ---------------------------------------------------------------------------
# RISK thresholds (operator behaviour)
# ---------------------------------------------------------------------------
# Idle time is judged by ratio to baseline.
IDLE_RATIO_WARNING = 1.8    # >1.8x normal -> notable
IDLE_RATIO_HIGH = 2.5       # >2.5x normal -> risk driver

# Harsh / high-load cycles counted in the recent window.
HARSH_CYCLES_WARNING = 4    # >=4 harsh cycles in window -> notable
HARSH_CYCLES_HIGH = 6       # >=6 -> risk driver

# Safety events (e.g. seatbelt deviation during high load).
SAFETY_EVENTS_HIGH = 1      # even one recent safety event is significant

# Risk score -> label bands (score is 0..100)
RISK_LABEL_BANDS = [
    (66, "HIGH"),
    (33, "MEDIUM"),
    (0, "LOW"),
]

# ---------------------------------------------------------------------------
# HEALTH thresholds (machine condition), judged by ratio/drift to baseline
# ---------------------------------------------------------------------------
HYDRAULIC_RATIO_WARNING = 1.5   # 1.5x baseline pressure -> warning
HYDRAULIC_RATIO_CRITICAL = 2.2  # 2.2x -> critical

VIBRATION_RATIO_WARNING = 1.5
VIBRATION_RATIO_CRITICAL = 2.0

ENGINE_TEMP_WARNING = 105.0     # deg C absolute ceiling
ENGINE_TEMP_CRITICAL = 115.0
OIL_PRESSURE_LOW_WARNING = 3.0  # bar; below this is a concern
OIL_PRESSURE_LOW_CRITICAL = 2.2

# Health status precedence: CRITICAL > WARNING > OK
HEALTH_STATUSES = ["OK", "WARNING", "CRITICAL"]

# ---------------------------------------------------------------------------
# LINK ANALYZER
# ---------------------------------------------------------------------------
# Correlation is asserted when BOTH an operator-risk driver and a machine-health
# driver are present in the same analysis window. This is a correlated /
# evidence-backed pattern, NEVER a causation claim.
LINK_REQUIRES_RISK_AT_LEAST = "MEDIUM"   # risk must be >= this
LINK_REQUIRES_HEALTH_AT_LEAST = "WARNING" # health must be >= this

# ---------------------------------------------------------------------------
# CONFIDENCE heuristic weights (must sum to 1.0). Transparent on purpose.
# confidence = w_distance * baseline_distance_norm
#            + w_corroboration * corroborating_signals_norm
#            + w_recency * recency_norm
# ---------------------------------------------------------------------------
CONF_W_DISTANCE = 0.40
CONF_W_CORROBORATION = 0.30
CONF_W_RECENCY = 0.30

# Normalisation caps
CONF_DISTANCE_CAP = 3.0     # a 3x-or-more deviation saturates the distance term
CONF_MAX_CORROBORATING = 4  # 4+ agreeing signals saturates the corroboration term
CONF_RECENCY_MAX_MINUTES = 60.0  # data older than this hits the stale floor
CONF_RECENCY_STALE_FLOOR = 0.5   # floor for fixed demo timestamps (see confidence.py)
