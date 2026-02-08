import talib

class IndicatorValidationError(Exception):
    pass

class IndicatorValidator:
    def __init__(self, registry, price_data):
        self.registry = registry
        self.price_data = price_data

    def validate(self, cfg):
        key = cfg["indicator"]
        tf = cfg["timeframe"]

        meta = (
            self.registry["indicators"].get(key)
            or self.registry["candlestick_patterns"].get(key)
        )
        if not meta:
            raise IndicatorValidationError(f"Unknown indicator: {key}")

        if tf not in self.price_data:
            raise IndicatorValidationError(f"Timeframe '{tf}' not found")

        df = self.price_data[tf]

        # Required inputs
        for col in meta["inputs"]["required"]:
            if col not in df.columns:
                raise IndicatorValidationError(
                    f"Missing input '{col}' for {key} on {tf}"
                )

        # Params type check
        for p, spec in meta.get("params", {}).items():
            if p in cfg.get("params", {}):
                val = cfg["params"][p]
                if spec["type"] == "int" and not isinstance(val, int):
                    raise IndicatorValidationError(f"{p} must be int")
                if spec["type"] == "float" and not isinstance(val, (float, int)):
                    raise IndicatorValidationError(f"{p} must be float")


class IndicatorExecutor:
    def __init__(self, registry):
        self.registry = registry

    def run(self, df, cfg):
        meta = (
            self.registry["indicators"].get(cfg["indicator"])
            or self.registry["candlestick_patterns"].get(cfg["indicator"])
        )

        func = getattr(talib, meta["function"])

        inputs = [df[col].values for col in meta["inputs"]["required"]]
        params = cfg.get("params", {})

        result = func(*inputs, **params)

        if not isinstance(result, tuple):
            result = (result,)

        return result, meta["outputs"]

class ColumnWriter:
    @staticmethod
    def write(df, name, outputs, values):
        for out, val in zip(outputs, values):
            col = name if len(outputs) == 1 else f"{name}_{out}"
            df[col] = val

