from flask import Flask, render_template_string
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
import os

app = Flask(__name__)

# 設置日誌記錄
logging.basicConfig(level=logging.INFO)

# LINE API 配置
LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('USER_ID')

# 定義異步抓取數據的函數
async def fetch(session, url, data_ids):
    try:
        logging.info(f"Fetching data from {url}")
        async with session.get(url, timeout=15) as response:
            response.raise_for_status()
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')
            data = {}
            for data_id in data_ids:
                element = soup.find('span', id=data_id)
                data[data_id] = element.text if element else f"找不到 id 為 {data_id} 的 span 元素"
            logging.info(f"Fetched data: {data}")
            return data
    except aiohttp.ClientError as e:
        logging.error(f"Client error fetching data from {url}: {e}")
        return {data_id: f"Client error occurred: {e}" for data_id in data_ids}
    except asyncio.TimeoutError as e:
        logging.error(f"Timeout error fetching data from {url}: {e}")
        return {data_id: f"Timeout error occurred: {e}" for data_id in data_ids}
    except Exception as e:
        logging.error(f"Unexpected error fetching data from {url}: {e}")
        return {data_id: f"Unexpected error occurred: {e}" for data_id in data_ids}

async def scrape_data(targets):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for target in targets:
            tasks.append(fetch(session, target['url'], target['data_ids']))
        return await asyncio.gather(*tasks)

async def send_line_message(data_list):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
    }
    
    id_to_chinese = {
        'lbl_online_date': '系統掛表日期',
        'lbl_daily_pw': '今日發電量kw',
        'lbl_today_price': '今日收入',
        'lbl_total_price': '掛表至今總收入',
        'lbl_system_time': '更新時間',
    }

    messages = []
    for data in data_list:
        message = '\n'.join([f"{id_to_chinese.get(key, key)}: {value}" for key, value in data.items()])
        messages.append(message)
    
    message_payload = {
        'to': USER_ID,
        'messages': [{'type': 'text', 'text': msg} for msg in messages]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(LINE_API_URL, headers=headers, json=message_payload) as response:
            if response.status != 200:
                logging.error(f"Failed to send message: {response.status}")
                logging.error(await response.text())
            else:
                logging.info("Message sent successfully")

# 定義路由和視圖函數
@app.route('/')
def index():
    logging.info("Index route accessed")
    targets = [
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?gw6UXnBQFxQcqRQvH_s-Zw&lang=traditional_chinese&time=0',
            'data_ids': ['lbl_online_date', 'lbl_daily_pw', 'lbl_today_price', 'lbl_total_price', 'lbl_system_time']
        },
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?9SGSfISfMFauB-qNFJwe2w&lang=traditional_chinese&time=',
            'data_ids': ['lbl_online_date', 'lbl_daily_pw', 'lbl_today_price', 'lbl_total_price', 'lbl_system_time']
        },
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?Us4azBhQh_643NPCj6EZzQ&lang=traditional_chinese&time=0',
            'data_ids': ['lbl_online_date', 'lbl_daily_pw', 'lbl_today_price', 'lbl_total_price', 'lbl_system_time']
        }
    ]

    try:
        data_list = asyncio.run(scrape_data(targets))
        asyncio.run(send_line_message(data_list))  # 发送消息到 LINE
    except Exception as e:
        logging.error(f"Error in scrape_data or send_line_message: {e}")
        return f"Error occurred: {e}"

    id_to_chinese = {
        'lbl_online_date': '系統掛表日期',
        'lbl_daily_pw': '今日發電量kw',
        'lbl_today_price': '今日收入',
        'lbl_total_price': '掛表至今總收入',
        'lbl_system_time': '更新時間',
    }
    html_content = """
    <!doctype html>
    <html lang="zh-tw">
    <head>
        <meta charset="utf-8">
        <title>太陽能三期數據整合</title>
        <style>
            body { font-family: Times New Roman, serif; font-size:20px; margin: 20px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { background: #f4f4f4; margin: 5px 0; padding: 10px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>太陽能三期數據整合</h1>
        {% for data in data_list %}
            <h2>太陽能第{{ loop.index }}期</h2>
            <ul>
                {% for key, value in data.items() %}
                <li>{{ id_to_chinese[key] }}: {{ value }}</li>
                {% endfor %}
            </ul>
        {% endfor %}
    </body>
    </html>
    """

    return render_template_string(html_content, data_list=data_list, id_to_chinese=id_to_chinese)

if __name__ == '__main__':
    logging.info("Starting Flask app")
    app.run(port=5000, debug=True)
