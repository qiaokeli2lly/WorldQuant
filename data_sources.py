# intelligence/data_sources.py
import tushare as ts
import pandas as pd
import os
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import finnhub
from newsapi import NewsApiClient
from deep_translator import GoogleTranslator

# ---------- 通用工具 ----------
def convert_code(symbol):
    """A股代码转 Tushare 格式，美股返回 None"""
    if symbol.isalpha():
        return None
    if symbol.startswith('6'):
        return f"{symbol}.SH"
    else:
        return f"{symbol}.SZ"

def _safe_request(url, headers, timeout=10, retries=2):
    for attempt in range(retries + 1):
        time.sleep(random.uniform(1.5, 3.0))
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < retries:
                wait = (2 ** attempt) * 2
                print(f"请求被限流，等待 {wait} 秒...")
                time.sleep(wait)
            else:
                print(f"请求失败 {url}: {e}")
                return None
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
            else:
                print(f"请求失败 {url}: {e}")
                return None
    return None

# ---------- Tushare 新闻接口 ----------
def fetch_tushare_news(symbol, limit=15):
    """从 Tushare 获取 A 股新闻（免费，不限次）"""
    pro = ts.pro_api()
    try:
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        ts_code = convert_code(symbol)
        if ts_code is None:
            return pd.DataFrame()
        df = pro.news(ts_code=ts_code,
                      start_date=start_date,
                      end_date=end_date,
                      limit=limit)
        if df is not None and not df.empty:
            df['source'] = 'Tushare'
            if 'headline' in df.columns:
                df = df.rename(columns={'headline': 'title'})
            if 'content' not in df.columns:
                df['content'] = ''
            df['content'] = df['content'].fillna('')
            return df[['title', 'content', 'source']]
        return pd.DataFrame()
    except Exception as e:
        print(f"Tushare新闻获取失败: {e}")
        return pd.DataFrame()

# ---------- 雪球 ----------
def fetch_xueqiu(symbol, limit=15):
    if symbol.isalpha():
        return pd.DataFrame()
    if symbol.startswith('6'):
        xq_code = f"SH{symbol}"
    else:
        xq_code = f"SZ{symbol}"
    url = f"https://xueqiu.com/v4/stock/quote.json?symbol={xq_code}&extend=detail"
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://xueqiu.com/',
    }
    session = requests.Session()
    try:
        session.get('https://xueqiu.com/', headers=headers, timeout=10)
        time.sleep(random.uniform(1, 2))
        resp = session.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"雪球API请求失败: {e}")
        return pd.DataFrame()
    try:
        data = resp.json()
        news_list = data.get('data', {}).get('news', [])
        if not news_list:
            news_list = data.get('data', {}).get('recent_news', [])
        if not news_list:
            print("雪球API返回中未找到新闻列表")
            return pd.DataFrame()
        items = []
        for n in news_list[:limit]:
            title = n.get('title', '')
            if not title:
                continue
            summary = n.get('text', '') or n.get('summary', '') or ''
            items.append({
                'title': title,
                'content': summary[:200],
                'source': '雪球'
            })
        print(f"雪球获取 {len(items)} 条")
        return pd.DataFrame(items) if items else pd.DataFrame()
    except Exception as e:
        print(f"雪球数据解析失败: {e}")
        return pd.DataFrame()

# ---------- 巨潮公告 ----------
def fetch_cninfo_announcements(symbol, limit=10):
    if symbol.isalpha():
        return pd.DataFrame()
    if symbol.startswith('6'):
        secode = f"{symbol}.SH"
    else:
        secode = f"{symbol}.SZ"
    url = f"http://www.cninfo.com.cn/new/disclosure/stock?stockCode={secode}&pageSize={limit}&pageNum=1"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = _safe_request(url, headers, timeout=15)
    if not resp:
        return pd.DataFrame()
    try:
        text = resp.text
        if text.startswith('callback('):
            text = text[9:-1]
        data = json.loads(text)
        items = data.get('announcements', []) or data.get('data', [])
        result = []
        for item in items[:limit]:
            title = item.get('announcementTitle', '') or item.get('title', '')
            if title:
                result.append({'title': title, 'content': '', 'source': '巨潮公告'})
        print(f"巨潮公告获取 {len(result)} 条")
        return pd.DataFrame(result) if result else pd.DataFrame()
    except Exception as e:
        print(f"巨潮公告解析失败: {e}")
        return pd.DataFrame()

# ---------- 东方财富 ----------
def fetch_eastmoney(symbol, limit=8):
    if symbol.isalpha():
        return pd.DataFrame()
    url = f"https://so.eastmoney.com/news/s?keyword={symbol}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = _safe_request(url, headers)
    if not resp:
        return pd.DataFrame()
    try:
        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.news-item, .search-result-item, li')
        data = []
        ad_keywords = ['开户', '交易', 'Level-2', '策略版', '妙想投研', 'Choice', '证券', '基金', '活期宝', '免费版']
        for item in items:
            a_tag = item.select_one('a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            if len(title) < 10:
                continue
            if any(kw in title for kw in ad_keywords):
                continue
            data.append({'title': title, 'content': '', 'source': '东方财富'})
        print(f"东方财富获取 {len(data)} 条")
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"东方财富解析失败: {e}")
        return pd.DataFrame()

# ---------- 新浪 ----------
def fetch_sina(symbol, limit=8):
    if symbol.isalpha():
        return pd.DataFrame()
    code = f"sh{symbol}" if symbol.startswith('6') else f"sz{symbol}"
    url = f"https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_AllNewsStock/symbol/{code}.phtml"
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = _safe_request(url, headers)
    if not resp:
        return pd.DataFrame()
    try:
        soup = BeautifulSoup(resp.text, 'lxml')
        items = soup.select('.datelist')[:limit]
        data = []
        for item in items:
            a_tag = item.select_one('a')
            if a_tag:
                data.append({'title': a_tag.get_text(strip=True), 'content': '', 'source': '新浪'})
        print(f"新浪获取 {len(data)} 条")
        return pd.DataFrame(data) if data else pd.DataFrame()
    except:
        return pd.DataFrame()

# ---------- Finnhub（美股新闻）----------
def fetch_finnhub_news(symbol, limit=15):
    if not symbol.isalpha():
        return pd.DataFrame()
    try:
        api_key = os.getenv('FINNHUB_API_KEY', '')
        if not api_key:
            return pd.DataFrame()
        client = finnhub.Client(api_key=api_key)
        end = datetime.now()
        start = end - timedelta(days=7)
        res = client.company_news(symbol, _from=start.strftime('%Y-%m-%d'), to=end.strftime('%Y-%m-%d'))
        if not res:
            return pd.DataFrame()
        data = []
        for item in res[:limit]:
            title = item.get('headline', '')
            if not title:
                continue
            data.append({
                'title': title,
                'content': (item.get('summary', '') or '')[:200],
                'source': 'Finnhub',
                'url': item.get('url', ''),
                'pub_date': datetime.fromtimestamp(item['datetime']).strftime('%Y-%m-%d')
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"Finnhub 获取失败: {e}")
        return pd.DataFrame()

# ---------- NewsAPI ----------
def fetch_newsapi_news(symbol, limit=15):
    try:
        api_key = os.getenv('NEWSAPI_KEY', '')
        if not api_key:
            return pd.DataFrame()
        newsapi = NewsApiClient(api_key=api_key)
        query = f"{symbol} 股票"
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        articles = newsapi.get_everything(q=query, language='zh',
                                          page_size=limit, sort_by='publishedAt',
                                          from_param=from_date)
        if not articles or 'articles' not in articles:
            return pd.DataFrame()
        data = []
        for art in articles['articles'][:limit]:
            title = art.get('title', '')
            if not title:
                continue
            data.append({
                'title': title,
                'content': (art.get('description', '') or '')[:200],
                'source': 'NewsAPI',
                'url': art.get('url', ''),
                'pub_date': (art.get('publishedAt', '') or '')[:10]
            })
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"NewsAPI 获取失败: {e}")
        return pd.DataFrame()

# ---------- Tushare 资金流向（保留）----------
def get_moneyflow(symbol, start_date, end_date):
    """获取个股资金流向（A股）"""
    pro = ts.pro_api()
    try:
        ts_code = convert_code(symbol)
        if ts_code is None:
            return pd.DataFrame()
        df = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df if not df.empty else pd.DataFrame()
    except:
        return pd.DataFrame()

# ---------- Tushare 概念板块（保留）----------
def get_concept(symbol):
    """获取个股所属概念板块（A股）"""
    pro = ts.pro_api()
    try:
        ts_code = convert_code(symbol)
        if ts_code is None:
            return []
        df = pro.concept_detail(ts_code=ts_code)
        if df is not None and not df.empty:
            return df['concept_name'].tolist()
        return []
    except:
        return []

# ---------- 翻译工具 ----------
def translate_text(text, target='zh-CN', timeout=5):
    if not text or not isinstance(text, str) or text.strip() == '':
        return text
    try:
        translated = GoogleTranslator(source='auto', target=target).translate(text)
        return translated
    except Exception as e:
        print(f"翻译失败: {e}")
        return text

def translate_news_dataframe(df):
    if df.empty:
        return df
    for col in ['title', 'content']:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(lambda x: translate_text(x) if isinstance(x, str) and any(ord(c) < 128 for c in x) else x)
    return df

# ---------- 并发聚合（按市场筛选源）----------
def get_all_news_concurrent(symbol, limit_per_source=15, max_total=40):
    if symbol.isalpha():
        sources = [
            ('finnhub', fetch_finnhub_news),
            ('newsapi', fetch_newsapi_news),
        ]
    else:
        sources = [
            ('tushare', fetch_tushare_news),
            ('xueqiu', fetch_xueqiu),
            ('cninfo', fetch_cninfo_announcements),
            ('eastmoney', fetch_eastmoney),
            ('sina', fetch_sina),
            ('newsapi', fetch_newsapi_news),
        ]

    all_news = []
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        future_map = {executor.submit(func, symbol, limit_per_source): name for name, func in sources}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                df = future.result()
                if not df.empty:
                    all_news.append(df)
                    print(f"{name} 获取 {len(df)} 条")
            except Exception as e:
                print(f"{name} 异常: {e}")

    if not all_news:
        return pd.DataFrame()
    combined = pd.concat(all_news, ignore_index=True)
    combined = combined.drop_duplicates(subset=['title'], keep='first')
    combined = translate_news_dataframe(combined)
    return combined.head(max_total)

# ---------- 股票名称缓存 ----------
STOCK_NAME_CACHE = "stock_name_cache.json"
def get_stock_name(symbol):
    if os.path.exists(STOCK_NAME_CACHE):
        with open(STOCK_NAME_CACHE, 'r') as f:
            cache = json.load(f)
        if symbol in cache:
            return cache[symbol]
    try:
        pro = ts.pro_api()
        ts_code = convert_code(symbol)
        if ts_code is None:
            return ""
        df = pro.stock_basic(ts_code=ts_code, fields='name')
        if df is not None and not df.empty:
            name = df.iloc[0]['name']
            cache = {} if not os.path.exists(STOCK_NAME_CACHE) else json.load(open(STOCK_NAME_CACHE))
            cache[symbol] = name
            with open(STOCK_NAME_CACHE, 'w') as f:
                json.dump(cache, f)
            return name
    except:
        pass
    return ""

def check_data_availability(symbol):
    return {'news': True, 'announcements': True, 'moneyflow': True, 'concept': True}