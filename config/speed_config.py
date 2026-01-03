# config/speed_config.py

# --- Round timing ---
ROUND_DURATION_SEC = 25

# --- Market update rate ---
MARKET_HZ = 12          # price updates per second (independent of FPS)

# --- Market dynamics ---
VOLATILITY = 0.35
DRIFT = 0.0
PEG_COUNT = 25

# --- Time compression ---
TIME_SCALE = 8.0        # higher = faster market



# # slow
# ROUND_DURATION_SEC = 40
# MARKET_HZ = 6
# TIME_SCALE = 4.0
# VOLATILITY = 0.25

# # Arcade
# ROUND_DURATION_SEC = 25
# MARKET_HZ = 12
# TIME_SCALE = 8.0
# VOLATILITY = 0.35
