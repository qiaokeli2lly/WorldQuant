# intelligence/local_db.py
import sqlite3
import os

DB_PATH = "local_finance.db"   # 数据库文件，与项目根目录同级

def get_connection():
    """获取数据库连接，自动创建文件"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # 让查询结果可以像字典一样访问
    return conn

def init_db():
    """创建所需的表（如果不存在）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 新闻/公告表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            title TEXT,
            summary TEXT,
            source TEXT,
            url TEXT UNIQUE,          -- 用URL去重，防止重复插入
            pub_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 财务指标表（后面再填充）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financials (
            symbol TEXT,
            report_date TEXT,
            pe REAL,
            pb REAL,
            roe REAL,
            PRIMARY KEY (symbol, report_date)
        )
    ''')
    
    # 宏观数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS macro_data (
            indicator TEXT,
            date TEXT,
            value REAL,
            PRIMARY KEY (indicator, date)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def insert_articles(articles_list):
    """
    批量插入新闻，自动忽略重复URL
    articles_list: [{'symbol':'600519', 'title':'...', 'summary':'...', 'source':'rss', 'url':'...', 'pub_date':'2025-01-01'}]
    """
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    for art in articles_list:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO articles (symbol, title, summary, source, url, pub_date) VALUES (?,?,?,?,?,?)",
                (art['symbol'], art['title'], art['summary'], art['source'], art['url'], art['pub_date'])
            )
            if cursor.rowcount > 0:
                count += 1
        except:
            pass
    conn.commit()
    conn.close()
    return count

def query_articles(symbol, limit=15):
    """查询某只股票的最新新闻"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title, summary as content, source FROM articles WHERE symbol=? ORDER BY pub_date DESC LIMIT ?",
        (symbol, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    # 转换为 DataFrame
    import pandas as pd
    if rows:
        return pd.DataFrame([dict(r) for r in rows])
    return pd.DataFrame()

if __name__ == "__main__":
    init_db()
# 在 intelligence/local_db.py 末尾追加

def init_sentiment_table():
    """创建情感缓存表（如果不存在）"""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sentiment_cache (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            score REAL,
            PRIMARY KEY (symbol, date)
        )
    ''')
    conn.commit()
    conn.close()

def save_sentiment(symbol, date, score):
    """保存或更新某股票某日的情感得分"""
    conn = get_connection()
    conn.execute('''
        INSERT OR REPLACE INTO sentiment_cache (symbol, date, score)
        VALUES (?, ?, ?)
    ''', (symbol, date, score))
    conn.commit()
    conn.close()

def get_sentiment(symbol, date):
    """查询某股票某日的情感得分，若无返回 None"""
    conn = get_connection()
    cur = conn.execute(
        'SELECT score FROM sentiment_cache WHERE symbol=? AND date=?',
        (symbol, date)
    )
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None