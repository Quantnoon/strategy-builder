import pandas as pd
import operator
from signal_registry import SESSION_DEFINITIONS


# ==============================
# OPERATORS
# ==============================

OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne
}


# ==============================
# TIME RESOLUTION
# ==============================

def get_time_series(df):
    if isinstance(df.index, pd.DatetimeIndex):
        return df.index

    for col in ("timestamp", "time", "datetime", "date"):
        if col in df.columns:
            return pd.to_datetime(df[col])

    raise ValueError("Session logic requires DatetimeIndex or timestamp column")


# ==============================
# SESSION COMPUTATION
# ==============================

def compute_session_levels(price_data, session_defs, base_timeframe):

    session_levels = {}
    base_df = price_data[base_timeframe].copy()
    base_df["_time"] = get_time_series(base_df)

    for name, cfg in session_defs.items():

        # -------- Higher TF (prev day, last week)
        if cfg["type"] == "higher_tf":

            tf = cfg["timeframe"]
            shift = cfg.get("shift", 0)

            df = price_data[tf][["open", "high", "low", "close"]].copy()
            df = df.shift(shift)

            # Align to base timeframe index
            df = df.reindex(base_df.index, method="ffill")

            session_levels[name] = df
            continue

        # -------- Intraday sessions
        start = pd.to_datetime(cfg["start"]).time()
        end = pd.to_datetime(cfg["end"]).time()

        session_high = []
        session_low = []
        session_open = []
        session_close = []

        for date, group in base_df.groupby(base_df["_time"].dt.date):

            mask = (
                (group["_time"].dt.time >= start) &
                (group["_time"].dt.time < end)
            )

            session_df = group[mask]

            if session_df.empty:
                session_high.extend([None] * len(group))
                session_low.extend([None] * len(group))
                session_open.extend([None] * len(group))
                session_close.extend([None] * len(group))
                continue

            high = session_df["high"].max()
            low = session_df["low"].min()
            open_ = session_df.iloc[0]["open"]
            close_ = session_df.iloc[-1]["close"]

            session_high.extend([high] * len(group))
            session_low.extend([low] * len(group))
            session_open.extend([open_] * len(group))
            session_close.extend([close_] * len(group))

        session_levels[name] = pd.DataFrame({
            "high": session_high,
            "low": session_low,
            "open": session_open,
            "close": session_close
        }, index=base_df.index)

    return session_levels


# ==============================
# REFERENCE RESOLUTION (VECTOR)
# ==============================

def resolve_reference(price_data, session_levels, ref, entry_tf):

    ref_type = ref["type"]

    # -------- Column
    if ref_type == "column":
        tf = ref.get("timeframe", entry_tf)
        col = ref["column"]
        return price_data[tf][col]

    # -------- Session
    if ref_type == "session":
        session = ref["session"]
        value = ref["value"]
        return session_levels[session][value]

    # -------- Literal
    if ref_type == "literal":
        value = ref["value"]
        return pd.Series(value, index=price_data[entry_tf].index)

    raise ValueError(f"Unknown reference type: {ref_type}")


# ==============================
# CONDITION EVALUATION (VECTOR)
# ==============================

def evaluate_condition(price_data, session_levels, node, entry_tf):

    left = resolve_reference(price_data, session_levels, node["left"], entry_tf)
    right = resolve_reference(price_data, session_levels, node["right"], entry_tf)

    return OPS[node["operator"]](left, right)


# ==============================
# LOGIC TREE (RECURSIVE VECTOR)
# ==============================

def evaluate_logic(price_data, session_levels, node, entry_tf):

    node_type = node["type"]

    if node_type in ("AND", "OR"):

        children = [
            evaluate_logic(price_data, session_levels, c, entry_tf)
            for c in node["children"]
        ]

        result = children[0]

        for child in children[1:]:
            if node_type == "AND":
                result = result & child
            else:
                result = result | child

        return result

    if node_type == "condition":
        return evaluate_condition(price_data, session_levels, node, entry_tf)

    raise ValueError(f"Unknown logic node type: {node_type}")


# ==============================
# FINAL SIGNAL GENERATOR
# ==============================

def generate_signal(price_data, strategy):

    entry_tf = strategy["entry_timeframe"]

    session_levels = compute_session_levels(
        price_data,
        SESSION_DEFINITIONS,
        base_timeframe=entry_tf
    )

    buy_series = evaluate_logic(
        price_data,
        session_levels,
        strategy["buy_logic"],
        entry_tf
    )

    sell_series = evaluate_logic(
        price_data,
        session_levels,
        strategy["sell_logic"],
        entry_tf
    )

    signal = pd.Series(0, index=price_data[entry_tf].index)

    signal[buy_series & ~sell_series] = 1
    signal[sell_series & ~buy_series] = -1

    price_data[entry_tf]["signal"] = signal

    return price_data
