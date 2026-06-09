# config.py
""" 集中管理全局常量与默认参数 """

# 数据缓存目录
DATA_CACHE_DIR = "data_cache"
FUNDAMENTAL_CACHE_DIR = "fundamental_cache"
INDEX_CACHE_DIR = "index_cache"

# 默认回测参数
DEFAULT_INITIAL_CAPITAL = 100000
DEFAULT_COMMISSION = 0.001
DEFAULT_SLIPPAGE = 0.001
DEFAULT_RISK_FREE_RATE = 0.03

# 调仓频率映射
REBALANCE_FREQ_MAP = {
    "每日": "D",
    "每周": "W",
    "每月": "M",
    "每季度": "Q"
}

# 默认因子权重（量价）
DEFAULT_FACTOR_WEIGHTS = {
    'momentum': 0.05,
    'reversal': 0.05,
    'volatility': 0.10,
    'rpv': 0.30,
    'new_momentum': 0.30,
    'combo': 0.20,
}

# 默认选股数量
DEFAULT_TOP_N = 15

# 因子名称中英文映射
FACTOR_NAME_CN = {
    'momentum': '动量',
    'reversal': '反转',
    'volatility': '波动率',
    'rpv': '价量相关(RPV)',
    'new_momentum': '新动量',
    'combo': '综合量价',
    'pe': '市盈率(PE)',
    'pb': '市净率(PB)',
}