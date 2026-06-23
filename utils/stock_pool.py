# utils/stock_pool.py
def get_predefined_pool(name='demo'):
    if name == 'demo':
        return [
            '600519', '000858', '601318', '600036', '000333',
            '002415', '300750', '601888', '600900', '601166',
            '000002', '002594', '600276', '601398', '600030',
            '601288', '600887', '601628', '000001', '002352',
            '600309', '601012', '600585', '000568', '002714',
            '300059', '601818', '600048', '601688', '600104',
            '000651', '002475', '300124', '600809', '002230',
            '300015', '600570', '000725', '603259', '600031',
            '002129', '601857', '600028', '601088', '601899',
            '600438', '002460', '300274', '600406', '002916'
        ]
    elif name == 'hs300':
        return get_predefined_pool('demo')
    elif name == 'us_top20':
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
            'TSLA', 'META', 'TSM', 'BABA', 'PDD',
            'NTES', 'JD', 'BIDU', 'NIO', 'LI',
            'XPEV', 'PLTR', 'AMD', 'KO', 'DIS'
        ]
    elif name == 'a_us_mixed':
        a_pool = get_predefined_pool('demo')[:30]
        us_pool = get_predefined_pool('us_top20')
        return a_pool + us_pool
    else:
        raise ValueError("Unknown pool")