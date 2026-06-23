# data/data_manager.py
class DataManager:
    """单例数据管理器，提供行情和基本面的统一内存缓存"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache_stock = {}        # {(sym, start, end): df}
            cls._instance._cache_fundamental = {}  # {sym: dict}
        return cls._instance

    def _is_us_stock(self, symbol: str) -> bool:
        return symbol.isalpha() and not symbol.isdigit()

    def get_stock_data(self, symbol: str, start_date: str, end_date: str):
        """获取行情数据，自动区分 A 股/美股，并缓存到内存"""
        key = (symbol, start_date, end_date)
        if key in self._cache_stock:
            return self._cache_stock[key]

        if self._is_us_stock(symbol):
            from data.us_stock_data import get_us_stock_data
            df = get_us_stock_data(symbol, start_date, end_date)
        else:
            from data.stock_data import get_stock_data
            df = get_stock_data(symbol, start_date, end_date)

        self._cache_stock[key] = df
        return df

    def get_fundamental(self, symbol: str):
        """获取基本面数据（仅 A 股），内存缓存"""
        if self._is_us_stock(symbol):
            return None

        if symbol not in self._cache_fundamental:
            from data.fundamental import get_fundamental_single
            self._cache_fundamental[symbol] = get_fundamental_single(symbol)
        return self._cache_fundamental[symbol]

    def clear_cache(self):
        self._cache_stock.clear()
        self._cache_fundamental.clear()