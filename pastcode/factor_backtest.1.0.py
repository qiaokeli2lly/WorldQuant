import baostock as bs
import pandas as pd

def test_baostock_fundamental():
    lg = bs.login()
    print(f"登录状态: {lg.error_msg}")
    if lg.error_code != '0':
        print("登录失败")
        return

    symbol = "600519"
    bs_code = f"sh.{symbol}"
    date = "2024-06-30"

    # 1. 获取 PB
    rs_k = bs.query_history_k_data_plus(bs_code,
                                        "date,pbMRQ",
                                        start_date=date, end_date=date,
                                        frequency="d", adjustflag="2")
    pb = None
    if rs_k.error_code == '0':
        if rs_k.next():
            row = rs_k.get_row_data()
            pb = row[1] if len(row) > 1 else None
            print(f"PB: {pb}")
        else:
            print("PB 查询无数据")
    else:
        print(f"PB 查询失败: {rs_k.error_msg}")

    # 2. 获取 ROE
    year = 2024
    quarter = 2
    rs_profit = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
    if rs_profit.error_code == '0':
        # rs_profit.fields 可能是列表
        fields = rs_profit.fields
        if isinstance(fields, str):
            fields = fields.split(',')
        # 查找 roeAvg 的索引
        try:
            idx = fields.index('roeAvg')
        except ValueError:
            idx = 3  # 常见位置
        if rs_profit.next():
            row = rs_profit.get_row_data()
            roe = row[idx] if len(row) > idx else None
            print(f"ROE: {roe}")
        else:
            print("ROE 无数据")
    else:
        print(f"ROE 查询失败: {rs_profit.error_msg}")

    bs.logout()

if __name__ == "__main__":
    test_baostock_fundamental()