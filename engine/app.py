from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import time
import pandas as pd
from indicator_registry import  INDICATOR_REGISTRY
from technical_indicators import IndicatorExecutor, IndicatorValidator, ColumnWriter
from trade_signal import generate_signal
from backtest import run_backtest

class Engine(ABC):
    _price_config: dict = {}
    _price_data: dict = {}
    _is_connected = False
    _registry = INDICATOR_REGISTRY
    _executor = IndicatorExecutor(INDICATOR_REGISTRY)
    _user_indicators = {}
    _pip_size = 0
    _pip_value = 0
    _tick_size = 0
    _tick_value = 0

    def _connect(self):
        print("connection established")
        self._is_connected = True

    @abstractmethod
    def _set_price_data(self):
        pass

    def set_custom_price_data(self, config: dict):
        self._price_config = config
        for idx, tf in enumerate(config.get("timeframes", [])):
            self._price_data[tf] = config.get("custom_prices", [])[idx]

    def set_price_data(self, config: dict):
        if not self._is_connected:
            return 'connection is required to set price configuration'
        self._price_config = config
        self._set_price_data()

    def get_price(self, tf=None):
        if not self._is_connected and not self._price_config.get("is_custom"):
            print('Connection is required')
            return False
        if not tf:
            return 'Timeframe is required'
        return self._price_data[tf]

    def set_technical_indicators(self, indicators):
        if not self._is_connected:
            return 'connection is required to set price configuration'
        validator = IndicatorValidator(self._registry, self._price_data)
        for cfg in indicators:
            # store the user-defined indicator
            self._user_indicators[cfg["name"]] = cfg

            # validate and compute
            validator.validate(cfg)
            df = self._price_data[cfg["timeframe"]]
            values, outputs = self._executor.run(df, cfg)
            ColumnWriter.write(df, cfg["name"], outputs, values)

    def get_indicator_output(self, timeframe, name):
        """
        Return the list of column names in _price_data[timeframe] for a user-defined indicator.
        Checks that the columns actually exist in that timeframe's DataFrame.
        """
        if name not in self._user_indicators:
            raise ValueError(f"Indicator '{name}' is not defined")

        if timeframe not in self._price_data:
            raise ValueError(f"Timeframe '{timeframe}' does not exist in price data")

        df = self._price_data[timeframe]
        cfg = self._user_indicators[name]

        meta = (
                self._registry["indicators"].get(cfg["indicator"])
                or self._registry["candlestick_patterns"].get(cfg["indicator"])
        )

        columns = []
        for out_name in meta["outputs"]:
            col_name = name if len(meta["outputs"]) == 1 else f"{name}_{out_name}"
            if col_name in df.columns:
                columns.append(col_name)
            else:
                # Optional: warn if column missing
                print(f"Warning: Column '{col_name}' not found in timeframe '{timeframe}'")

        return columns

    def set_signal(self, signal):
        generate_signal(self._price_data, signal)
        
    def run_backtest(self, backtest_config, account_config):
        trades = run_backtest(
            self._price_data[backtest_config.get("timeframe")],
            pip_size=self._pip_size,
            pip_value=self._pip_value,
            tick_size=self._tick_size,
            tick_value=self._tick_value,
            account_size=account_config.get("account_size"),
            lot_size=account_config.get("lot_size"),
            spread_pips=account_config.get("spread_pips"),
            slippage_pips=account_config.get("slippage_pips"),
            config=backtest_config,
            mode=backtest_config.get("mode")
        )
        
        return trades

class MT5Engine(Engine):
    __mt5 = {}
    def __init__(self, mt5):
        self.__mt5 = mt5
        super().__init__()

    def connect(self, login, password, server, path):
        if self.__mt5.initialize(login=login, password=password, server=server, path=path):
            self._connect()
        time.sleep(2)

    def _set_price_data(self):
        daterange = self._price_config.get("daterange")
        start_time, end_time = get_time_range(daterange)
        timeframes = self._price_config.get("timeframes")
        symbol = self._price_config.get("symbol")
        
        self._pip_size = get_pip(self.__mt5, symbol)
        self._pip_value = get_pip_value(self.__mt5, symbol)
        self._tick_size = self.__mt5.symbol_info(symbol).trade_tick_size
        self._tick_value = self.__mt5.symbol_info(symbol).trade_tick_value
    
        # Fetch all ticks once for the range
        ticks = self.__mt5.copy_ticks_range(symbol, start_time, end_time, self.__mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            raise ValueError("No tick data retrieved. Please check symbol and connection.")
    
        tick_df = pd.DataFrame(ticks)
        tick_df['time'] = pd.to_datetime(tick_df['time'], unit='s')
        tick_df = tick_df.sort_values('time')
    
        for timeframe in timeframes:
            # Fetch candles
            rates = self.__mt5.copy_rates_range(symbol, get_mt5_timeframe(self.__mt5, timeframe), start_time, end_time)
            if rates is None or len(rates) == 0:
                raise ValueError(f"No candle data retrieved for {timeframe}")
    
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.sort_values('time')
    
            # Efficiently get last bid/ask for each candle using merge_asof
            df = pd.merge_asof(df, tick_df[['time', 'bid', 'ask']], on='time', direction='backward')
    
            self._price_data[timeframe] = df


def get_mt5_timeframe(mt5, tf_string):
    mapping = {
        "W1": mt5.TIMEFRAME_W1,
        "D1": mt5.TIMEFRAME_D1,
        "H4": mt5.TIMEFRAME_H4,
        "H1": mt5.TIMEFRAME_H1,
        "M15": mt5.TIMEFRAME_M15,
        "M5": mt5.TIMEFRAME_M5,
        "M1": mt5.TIMEFRAME_M1
    }
    return mapping.get(tf_string, None)

def get_time_range(offset_str):
    """
    Returns (start_time, end_time) in UTC.

    Supported offset_str:
    - '5M' = 5 months
    - '3H' = 3 hours
    - '10D' = 10 days
    - '2W' = 2 weeks
    - '1Y' = 1 year

    start_time is set to 00:00:00
    end_time is current UTC time
    """
    tz = pytz.utc
    now = datetime.now(tz)

    unit = offset_str[-1].upper()
    value = int(offset_str[:-1])

    if unit == "M":
        delta = relativedelta(months=value)
    elif unit == "Y":
        delta = relativedelta(years=value)
    elif unit == "W":
        delta = timedelta(weeks=value)
    elif unit == "D":
        delta = timedelta(days=value)
    else:
        raise ValueError(f"Unsupported time unit '{unit}' in '{offset_str}'")

    start_dt = now - delta

    # Set time to midnight
    start_time = datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0, tzinfo=tz)
    end_time = now

    return start_time, end_time

def is_daterange_greater_than(daterange, years=0, months=0):
    now = datetime.now(pytz.utc)
    target_time, _ = get_time_range(daterange)
    threshold_time = now - relativedelta(years=years, months=months)
    return target_time < threshold_time

def get_pip(mt5, symbol):
    return 10*mt5.symbol_info(symbol).point

def get_pip_value(mt5, symbol):
    tick_value = mt5.symbol_info(symbol).trade_tick_value
    tick_size = mt5.symbol_info(symbol).trade_tick_size
    return tick_value / tick_size * get_pip(mt5, symbol)
