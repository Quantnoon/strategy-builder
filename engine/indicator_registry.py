INDICATOR_REGISTRY = {
    "indicators": {},
    "candlestick_patterns": {}
}

# TREND INDICATORS
INDICATOR_REGISTRY["indicators"]["SMA"] = {
    "name": "Simple Moving Average",
    "category": "trend",
    "library": "talib",
    "function": "SMA",
    "inputs": {"required": ["close"]},
    "params": {
        "timeperiod": {"type": "int", "default": 14, "min": 1, "max": 500}
    },
    "outputs": ["sma"],
    "ui": {"group": "Moving Averages", "overlay": True}
}
INDICATOR_REGISTRY["indicators"]["EMA"] = {
    "name": "Exponential Moving Average",
    "category": "trend",
    "library": "talib",
    "function": "EMA",
    "inputs": {"required": ["close"]},
    "params": {
        "timeperiod": {"type": "int", "default": 14, "min": 1, "max": 500}
    },
    "outputs": ["ema"],
    "ui": {"group": "Moving Averages", "overlay": True}
}
INDICATOR_REGISTRY["indicators"]["WMA"] = {
    "name": "Weighted Moving Average",
    "category": "trend",
    "library": "talib",
    "function": "WMA",
    "inputs": {"required": ["close"]},
    "params": {
        "timeperiod": {"type": "int", "default": 14}
    },
    "outputs": ["wma"],
    "ui": {"group": "Moving Averages", "overlay": True}
}
for ind in ["DEMA", "TEMA", "KAMA"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "trend",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["close"]},
        "params": {
            "timeperiod": {"type": "int", "default": 14}
        },
        "outputs": [ind.lower()],
        "ui": {"group": "Moving Averages", "overlay": True}
    }
INDICATOR_REGISTRY["indicators"]["SAR"] = {
    "name": "Parabolic SAR",
    "category": "trend",
    "library": "talib",
    "function": "SAR",
    "inputs": {"required": ["high", "low"]},
    "params": {
        "acceleration": {"type": "float", "default": 0.02},
        "maximum": {"type": "float", "default": 0.2}
    },
    "outputs": ["sar"],
    "ui": {"group": "Trend", "overlay": True}
}
INDICATOR_REGISTRY["indicators"]["ADX"] = {
    "name": "Average Directional Index",
    "category": "trend",
    "library": "talib",
    "function": "ADX",
    "inputs": {"required": ["high", "low", "close"]},
    "params": {"timeperiod": {"type": "int", "default": 14}},
    "outputs": ["adx"],
    "ui": {"group": "Trend Strength", "overlay": False}
}
for ind in ["PLUS_DI", "MINUS_DI"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "trend",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["high", "low", "close"]},
        "params": {"timeperiod": {"type": "int", "default": 14}},
        "outputs": [ind.lower()],
        "ui": {"group": "Trend Strength", "overlay": False}
    }

# Momentum Indicators
INDICATOR_REGISTRY["indicators"]["RSI"] = {
    "name": "Relative Strength Index",
    "category": "momentum",
    "library": "talib",
    "function": "RSI",
    "inputs": {"required": ["close"]},
    "params": {"timeperiod": {"type": "int", "default": 14}},
    "outputs": ["rsi"],
    "ui": {"group": "Momentum", "overlay": False}
}
INDICATOR_REGISTRY["indicators"]["MACD"] = {
    "name": "MACD",
    "category": "momentum",
    "library": "talib",
    "function": "MACD",
    "inputs": {"required": ["close"]},
    "params": {
        "fastperiod": {"type": "int", "default": 12},
        "slowperiod": {"type": "int", "default": 26},
        "signalperiod": {"type": "int", "default": 9}
    },
    "outputs": ["macd", "signal", "hist"],
    "ui": {"group": "Momentum", "overlay": False}
}
for ind in ["STOCH", "STOCHF"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "momentum",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["high", "low", "close"]},
        "params": {},
        "outputs": ["slowk", "slowd"] if ind == "STOCH" else ["fastk", "fastd"],
        "ui": {"group": "Momentum", "overlay": False}
    }
for ind in ["CCI", "ROC", "MOM", "TRIX"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "momentum",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["close"]},
        "params": {"timeperiod": {"type": "int", "default": 14}},
        "outputs": [ind.lower()],
        "ui": {"group": "Momentum", "overlay": False}
    }
for ind in ["ATR", "NATR"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "volatility",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["high", "low", "close"]},
        "params": {"timeperiod": {"type": "int", "default": 14}},
        "outputs": [ind.lower()],
        "ui": {"group": "Volatility", "overlay": False}
    }
INDICATOR_REGISTRY["indicators"]["BBANDS"] = {
    "name": "Bollinger Bands",
    "category": "volatility",
    "library": "talib",
    "function": "BBANDS",
    "inputs": {"required": ["close"]},
    "params": {
        "timeperiod": {"type": "int", "default": 20},
        "nbdevup": {"type": "float", "default": 2},
        "nbdevdn": {"type": "float", "default": 2}
    },
    "outputs": ["upper", "middle", "lower"],
    "ui": {"group": "Volatility", "overlay": True}
}

# Volume Indicators
for ind in ["OBV", "MFI", "AD", "ADOSC"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "volume",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["high", "low", "close", "volume"]},
        "params": {},
        "outputs": [ind.lower()],
        "ui": {"group": "Volume", "overlay": False}
    }

# Price Transforms
for ind in ["LINEARREG", "LINEARREG_SLOPE"]:
    INDICATOR_REGISTRY["indicators"][ind] = {
        "name": ind,
        "category": "price_transform",
        "library": "talib",
        "function": ind,
        "inputs": {"required": ["close"]},
        "params": {"timeperiod": {"type": "int", "default": 14}},
        "outputs": [ind.lower()],
        "ui": {"group": "Price Transform", "overlay": False}
    }

# CANDLESTICK PATTERNS
def _cdl(name, desc):
    return {
        "name": desc,
        "category": "candlestick",
        "library": "talib",
        "function": name,
        "inputs": {"required": ["open", "high", "low", "close"]},
        "params": {},
        "outputs": ["signal"],
        "signal_meaning": {100: "Bullish", -100: "Bearish", 0: "None"},
        "ui": {"group": "Candlestick Patterns"}
    }
for cdl, desc in {
    "CDLENGULFING": "Engulfing",
    "CDLHAMMER": "Hammer",
    "CDLINVERTEDHAMMER": "Inverted Hammer",
    "CDLSHOOTINGSTAR": "Shooting Star",
    "CDLDOJI": "Doji",
    "CDLDRAGONFLYDOJI": "Dragonfly Doji",
    "CDLGRAVESTONEDOJI": "Gravestone Doji",
    "CDLMORNINGSTAR": "Morning Star",
    "CDLEVENINGSTAR": "Evening Star",
    "CDLPIERCING": "Piercing",
    "CDLDARKCLOUDCOVER": "Dark Cloud Cover",
    "CDL3WHITESOLDIERS": "Three White Soldiers",
    "CDL3BLACKCROWS": "Three Black Crows",
    "CDLHARAMI": "Harami",
    "CDLHARAMICROSS": "Harami Cross",
    "CDLSPINNINGTOP": "Spinning Top",
    "CDLTAKURI": "Takuri",
    "CDLUPSIDEGAP2CROWS": "Upside Gap Two Crows",
    "CDLSEPARATINGLINES": "Separating Lines"
}.items():
    INDICATOR_REGISTRY["candlestick_patterns"][cdl] = _cdl(cdl, desc)

