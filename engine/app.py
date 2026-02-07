from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
import time
import pandas as pd

class Engine(ABC):
    _price_config: dict = {}
    _price_data: dict = {}
    _is_connected = False

    def _connect(self):
        print("connection established")
        self._is_connected = True

    @abstractmethod
    def _set_price_data(self):
        pass

    def set_price_data(self, config: dict):
        if not self._is_connected and not config.get("is_custom"):
            return 'connection is required to set price configuration'
        self._price_config = config
        self._set_price_data()

    def get_price(self, tf=None):
        if not self._is_connected:
            print('Connection is required')
            return False
        if not tf:
            return 'Timeframe is required'
        return self._price_data[tf]


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

        for timeframe in timeframes:
            rates = self.__mt5.copy_rates_range(symbol, get_mt5_timeframe(self.__mt5, timeframe), start_time, end_time)
            if rates is None or len(rates) == 0:
                raise ValueError("No data retrieved. Please check the symbol and connection.")

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            self._price_data[timeframe] = df


def get_mt5_timeframe(mt5, tf_string):
    mapping = {
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
