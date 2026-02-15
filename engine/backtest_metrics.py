import numpy as np

sessions = {
    "Asia": ("00:00", "08:00"),
    "London": ("08:00", "16:00"),
    "New_York": ("13:00", "21:00")
}

# ----------------------------
# Compute all metrics
# ----------------------------
def compute_backtest_metrics(trades_df, sessions=sessions):
    if trades_df.empty:
        return {}

    df = trades_df.copy().sort_values("exit_time").reset_index(drop=True)

    # ==============================
    # TRADE STATS
    # ==============================
    trade_stats = {}

    trade_stats['total_trades'] = len(df)
    trade_stats['total_buy_trades'] = len(df[df['direction']==1])
    trade_stats['total_sell_trades'] = len(df[df['direction']==-1])
    trade_stats['winning_trades'] = len(df[df['pnl']>0])
    trade_stats['losing_trades'] = len(df[df['pnl']<0])

    trade_stats['win_rate'] = trade_stats['winning_trades'] / trade_stats['total_trades']
    trade_stats['loss_rate'] = trade_stats['losing_trades'] / trade_stats['total_trades']

    # Consecutive wins/losses
    wins = df['pnl'] > 0
    losses = df['pnl'] < 0
    trade_stats['max_consecutive_wins'] = _max_consecutive(wins)
    trade_stats['max_consecutive_losses'] = _max_consecutive(losses)

    df['duration'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 60
    trade_stats['average_trade_duration_min'] = df['duration'].mean()

    df['month'] = df['exit_time'].dt.to_period("M")
    trade_stats['trades_per_month'] = df.groupby('month').size().mean()

    # ==============================
    # PNL METRICS
    # ==============================
    pnl_metrics = {}

    pnl_metrics['gross_profit'] = df[df['pnl']>0]['pnl'].sum()
    pnl_metrics['gross_loss'] = df[df['pnl']<0]['pnl'].sum()
    pnl_metrics['net_profit'] = df['pnl'].sum()

    pnl_metrics['largest_win'] = df['pnl'].max()
    pnl_metrics['largest_loss'] = df['pnl'].min()

    pnl_metrics['average_win'] = df[df['pnl']>0]['pnl'].mean() if trade_stats['winning_trades']>0 else 0
    pnl_metrics['average_loss'] = df[df['pnl']<0]['pnl'].mean() if trade_stats['losing_trades']>0 else 0

    pnl_metrics['profit_factor'] = (
        pnl_metrics['gross_profit'] / abs(pnl_metrics['gross_loss'])
        if pnl_metrics['gross_loss'] != 0 else np.inf
    )

    pnl_metrics['expected_value'] = (
        pnl_metrics['average_win'] * trade_stats['win_rate'] +
        pnl_metrics['average_loss'] * trade_stats['loss_rate']
    )

    pnl_metrics['expectancy'] = (
        pnl_metrics['average_win'] * trade_stats['win_rate'] -
        abs(pnl_metrics['average_loss']) * trade_stats['loss_rate']
    )

    starting_balance = df.iloc[0]["balance"] - df.iloc[0]["pnl"]
    pnl_metrics['return_on_account'] = pnl_metrics['net_profit'] / starting_balance

    # ==============================
    # RISK METRICS
    # ==============================
    risk_metrics = {}

    df['equity'] = df['balance']
    df['equity_peak'] = df['equity'].cummax()
    df['drawdown'] = df['equity'] - df['equity_peak']
    df['drawdown_pct'] = df['drawdown'] / df['equity_peak'] * 100

    risk_metrics['max_drawdown'] = df['drawdown'].min()
    risk_metrics['max_drawdown_pct'] = df['drawdown_pct'].min()

    # Drawdown duration (in trades)
    dd_duration = 0
    temp = 0
    for d in df['drawdown']:
        if d < 0:
            temp += 1
            dd_duration = max(dd_duration, temp)
        else:
            temp = 0
    risk_metrics['drawdown_duration_trades'] = dd_duration

    avg_loss = abs(pnl_metrics['average_loss'])
    edge = pnl_metrics['expected_value']

    risk_metrics['risk_of_ruin'] = (
        np.exp(-2 * edge * starting_balance / (avg_loss ** 2))
        if avg_loss != 0 else 0
    )

    # ==============================
    # PERFORMANCE METRICS
    # ==============================
    performance_metrics = {}

    df['date'] = df['exit_time'].dt.date
    daily_returns = df.groupby('date')['pnl'].sum()

    mean_daily = daily_returns.mean()
    std_daily = daily_returns.std()

    performance_metrics['sharpe_ratio'] = mean_daily / std_daily if std_daily != 0 else 0

    downside = daily_returns[daily_returns < 0]
    performance_metrics['sortino_ratio'] = (
        mean_daily / downside.std()
        if len(downside) > 0 and downside.std() != 0 else 0
    )

    df['risk'] = abs(df['entry_price'] - df['sl'])
    df['reward'] = abs(df['tp'] - df['entry_price'])
    df['rr'] = df['reward'] / df['risk']

    performance_metrics['risk_reward_ratio_avg'] = df['rr'].mean()
    performance_metrics['risk_reward_ratio_weighted'] = (
        (df['rr'] * abs(df['pnl'])).sum() / abs(df['pnl']).sum()
    )

    df['price_move'] = abs(df['exit_price'] - df['entry_price'])
    df['efficiency'] = df['pnl'] / df['price_move']
    performance_metrics['trade_efficiency'] = df['efficiency'].mean()

    # ==============================
    # SESSION METRICS
    # ==============================
    session_metrics = {}

    if sessions is not None:
        df['entry_hour'] = df['entry_time'].dt.hour + df['entry_time'].dt.minute/60

        for name, (start, end) in sessions.items():
            start_h, start_m = map(int, start.split(":"))
            end_h, end_m = map(int, end.split(":"))

            start_decimal = start_h + start_m/60
            end_decimal = end_h + end_m/60

            s_df = df[
                (df['entry_hour'] >= start_decimal) &
                (df['entry_hour'] < end_decimal)
            ]

            session_metrics[name] = {
                "total_trades": len(s_df),
                "net_profit": s_df['pnl'].sum(),
                "win_rate": (len(s_df[s_df['pnl']>0]) / len(s_df)) if len(s_df)>0 else 0
            }

    # ==============================
    # FINAL STRUCTURE
    # ==============================
    return {
        "trade_stats": trade_stats,
        "pnl_metrics": pnl_metrics,
        "risk_metrics": risk_metrics,
        "performance_metrics": performance_metrics,
        "session_metrics": session_metrics,
        "equity_curve": df['equity'].tolist()
    }

# ----------------------------
# Helper function
# ----------------------------
def _max_consecutive(series):
    """
    Count max consecutive True values in boolean series
    """
    max_count = count = 0
    for val in series:
        if val:
            count += 1
            max_count = max(max_count, count)
        else:
            count = 0
    return max_count
