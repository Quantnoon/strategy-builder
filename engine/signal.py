import pandas as pd
from signal_registry import SESSION_DEFINITIONS
import operator

OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne
}

def get_time_series(df):
    """
    Resolve timestamps from existing structure.
    Works with RangeIndex + timestamp column.
    """

    if isinstance(df.index, pd.DatetimeIndex):
        return df.index

    for col in ("timestamp", "time", "datetime", "date"):
        if col in df.columns:
            return pd.to_datetime(df[col])

    raise ValueError(
        "Session logic requires DatetimeIndex or timestamp column"
    )


def compute_session_levels(price_data, session_defs, base_timeframe):
    session_levels = {}

    base_df = price_data[base_timeframe].copy()
    base_df["_time"] = get_time_series(base_df)

    for name, cfg in session_defs.items():

        # -------------------------
        # HIGHER TF (prev day, last week)
        # -------------------------
        if cfg["type"] == "higher_tf":
            tf = cfg["timeframe"]
            shift = cfg.get("shift", 0)

            df = price_data[tf][["open", "high", "low", "close"]].copy()
            df = df.shift(shift)

            session_levels[name] = df
            continue

        # -------------------------
        # INTRADAY (London / NY / Asia)
        # -------------------------
        start = pd.to_datetime(cfg["start"]).time()
        end = pd.to_datetime(cfg["end"]).time()

        rows = []

        for date, group in base_df.groupby(base_df["_time"].dt.date):

            session_df = group[
                (group["_time"].dt.time >= start) &
                (group["_time"].dt.time < end)
            ]

            if session_df.empty:
                continue

            rows.append({
                "timestamp": session_df["_time"].iloc[-1],
                "open": session_df.iloc[0]["open"],
                "high": session_df["high"].max(),
                "low": session_df["low"].min(),
                "close": session_df.iloc[-1]["close"]
            })

        session_levels[name] = (
            pd.DataFrame(rows)
            .set_index("timestamp")
            .sort_index()
        )

    return session_levels

def resolve_session_reference(session_levels, ref_cfg, entry_index):
    """
    Example ref_cfg:
    {
        "type": "session",
        "session": "london",
        "value": "high"
    }
    """

    session_name = ref_cfg["session"]
    value = ref_cfg["value"]

    if session_name not in session_levels:
        return None

    df = session_levels[session_name]

    if df.empty or value not in df.columns:
        return None

    if isinstance(df.index, pd.DatetimeIndex):
        df = df[df.index <= entry_index]
        if df.empty:
            return None
        return df.iloc[-1][value]

    return None


def resolve_reference(price_data, session_levels, ref, entry_tf, entry_index):

    ref_type = ref["type"]

    # -------- Price column
    if ref_type == "column":
        tf = ref.get("timeframe", entry_tf)
        col = ref["column"]
        return price_data[tf].iloc[-1][col]

    # -------- Session level
    if ref_type == "session":
        session = ref["session"]
        value = ref["value"]

        if session not in session_levels:
            return None

        df = session_levels[session]
        if df.empty or value not in df.columns:
            return None

        df = df[df.index <= entry_index]
        if df.empty:
            return None

        return df.iloc[-1][value]

    raise ValueError(f"Unknown reference type: {ref_type}")

def evaluate_condition(price_data, session_levels, node, entry_tf):

    entry_index = price_data[entry_tf].iloc[-1].name

    left = resolve_reference(
        price_data,
        session_levels,
        node["left"],
        entry_tf,
        entry_index
    )

    right = resolve_reference(
        price_data,
        session_levels,
        node["right"],
        entry_tf,
        entry_index
    )

    if left is None or right is None:
        return False

    return OPS[node["operator"]](left, right)

def evaluate_logic(price_data, session_levels, node, entry_tf):

    node_type = node["type"]

    # -------- AND / OR
    if node_type in ("AND", "OR"):
        results = [
            evaluate_logic(price_data, session_levels, c, entry_tf)
            for c in node["children"]
        ]

        return all(results) if node_type == "AND" else any(results)

    # -------- Condition
    if node_type == "condition":
        return evaluate_condition(
            price_data,
            session_levels,
            node,
            entry_tf
        )

    raise ValueError(f"Unknown logic node type: {node_type}")

def generate_can_trade(price_data, signal):

    entry_tf = signal["entry_timeframe"]

    session_levels = compute_session_levels(
        price_data,
        SESSION_DEFINITIONS,
        base_timeframe=entry_tf
    )

    can_trade = evaluate_logic(
        price_data,
        session_levels,
        signal["logic"],
        entry_tf
    )

    price_data[entry_tf]["can_trade"] = can_trade
    return price_data
