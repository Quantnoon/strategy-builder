import pandas as pd

# ----------------------------
# ATR calculation
# ----------------------------
def compute_atr(df, period=14):
    """Assume df has 'high', 'low', 'close' columns"""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr.bfill()

def convert_to_pip(dollar_risk, lot_size, tick_size, tick_value, point):
    if tick_value == 0 or tick_size == 0:
        print("Error: Tick value or tick size is zero.")
        return 0

    pips = (dollar_risk / (tick_value * lot_size)) * (tick_size / point)

    return pips * point

# ----------------------------
# Universal backtester
# ----------------------------
def run_backtest(price_data, pip_size, pip_value, tick_size, tick_value, account_size, lot_size, spread_pips, slippage_pips, config, mode="candle"):
    """
    price_data: DataFrame with columns:
        - Candle: 'open','high','low','close','signal','time'
        - Tick: 'bid','ask','signal','time'
    mode: "candle" or "tick"
    """
    balance = account_size
    trades = []
    open_trades = []

    df = price_data.sort_values("time").reset_index(drop=True)

    # ATR for SL/TP if needed
    if any(tp.get("type")=="atr" for tp in config.get("take_profit",[])) or any(sl.get("type")=="atr" for sl in config.get("stop_loss",[])):
        if mode=="tick":
            df["close"] = df["bid"]
            df["high"] = df["bid"]
            df["low"] = df["bid"]
        df["atr"] = compute_atr(df, period=14)

    for idx, row in df.iterrows():

        # --------------------------
        # Check for entry
        # --------------------------
        if row["signal"] != 0:
            direction = row["signal"]

            # Check single trade per direction
            if config.get("single_trade_per_direction", False):
                if any(t["direction"] == direction for t in open_trades):
                    continue  # skip new trade for this direction

            # Entry price
            if mode=="tick":
                entry_price = row["ask"] if direction==1 else row["bid"]
            else:
                entry_price = row["close"]

            # Apply slippage + spread
            entry_price += (slippage_pips + spread_pips/2)*pip_size if direction==1 else -(slippage_pips + spread_pips/2)*pip_size

            trade = {
                "entry_time": row["time"],
                "direction": direction,
                "entry_price": entry_price,
                "sl": None,
                "tp": None,
                "exit_time": None,
                "exit_price": None,
                "pnl": None,
                "balance": balance,
                "reason": None
            }

            # Compute SL
            sl_prices = []
            for sl_cfg in config.get("stop_loss", []):
                if sl_cfg["type"]=="pips":
                    price = entry_price - sl_cfg["value"]*pip_size if direction==1 else entry_price + sl_cfg["value"]*pip_size
                    sl_prices.append(price)
                elif sl_cfg["type"]=="fixed":
                    price = entry_price - sl_cfg["value"] if direction==1 else entry_price + sl_cfg["value"]
                    sl_prices.append(price)
                elif sl_cfg["type"]=="dollar":
                    price_move = convert_to_pip(sl_cfg["value"], lot_size, tick_size=tick_size, tick_value=tick_value, point=pip_size)
                    price = entry_price - price_move if direction==1 else entry_price + price_move
                    sl_prices.append(price)
                elif sl_cfg["type"]=="atr":
                    atr_val = row["atr"] * sl_cfg["multiplier"]
                    price = entry_price - atr_val if direction==1 else entry_price + atr_val
                    sl_prices.append(price)

            trade["sl"] = min(sl_prices) if direction==1 else max(sl_prices)

            # Compute TP
            tp_prices = []
            for tp_cfg in config.get("take_profit", []):
                if tp_cfg["type"]=="pips":
                    price = entry_price + tp_cfg["value"]*pip_size if direction==1 else entry_price - tp_cfg["value"]*pip_size
                    tp_prices.append(price)
                elif tp_cfg["type"]=="fixed":
                    price = entry_price + tp_cfg["value"] if direction==1 else entry_price - tp_cfg["value"]
                    tp_prices.append(price)
                elif tp_cfg["type"]=="dollar":
                    price_move = convert_to_pip(tp_cfg["value"], lot_size, tick_size=tick_size, tick_value=tick_value, point=pip_size)
                    price = entry_price + price_move if direction==1 else entry_price - price_move
                    tp_prices.append(price)
                elif tp_cfg["type"]=="atr":
                    atr_val = row["atr"] * tp_cfg["multiplier"]
                    price = entry_price + atr_val if direction==1 else entry_price - atr_val
                    tp_prices.append(price)

            trade["tp"] = max(tp_prices) if direction==1 else min(tp_prices)
            open_trades.append(trade)

        # --------------------------
        # Check open trades for exit
        # --------------------------
        for t in open_trades.copy():
            if mode=="tick":
                high = row["ask"] if t["direction"]==1 else row["bid"]
                low = row["bid"] if t["direction"]==1 else row["ask"]
            else:
                high = row["high"]
                low = row["low"]

            exit_price = None
            reason = None

            # SL hit
            if t["direction"]==1 and low <= t["sl"]:
                exit_price = t["sl"]
                reason = "SL"
            elif t["direction"]==-1 and high >= t["sl"]:
                exit_price = t["sl"]
                reason = "SL"

            # TP hit
            if t["direction"]==1 and high >= t["tp"]:
                exit_price = t["tp"]
                reason = "TP"
            elif t["direction"]==-1 and low <= t["tp"]:
                exit_price = t["tp"]
                reason = "TP"

            if exit_price is not None:
                pnl = (exit_price - t["entry_price"])*t["direction"]*lot_size/pip_size*pip_value
                balance += pnl
                t["exit_time"] = row["time"]
                t["exit_price"] = exit_price
                t["pnl"] = pnl
                t["balance"] = balance
                t["reason"] = reason

                trades.append(t)
                open_trades.remove(t)

    return pd.DataFrame(trades)
