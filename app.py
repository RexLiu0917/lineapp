from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import logging

app = Flask(__name__)

# 設置日誌記錄
logging.basicConfig(level=logging.INFO)

# LINE API 配置
LINE_API_URL = 'https://api.line.me/v2/bot/message/push'
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
GROUP_ID = os.getenv('GROUP_ID')

# 定義抓取數據的函數
def scrape_data(url, data_ids):
    retry_strategy = requests.packages.urllib3.util.retry.Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)
    try:
        response = http.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {}
        for data_id in data_ids:
            element = soup.find('span', id=data_id)
            data[data_id] = element.text if element else f"找不到 id 為 {data_id} 的 span 元素"
        return data
    except requests.exceptions.RequestException as e:
        return {data_id: f"Error occurred: {e}" for data_id in data_ids}

# 定義發送 LINE 消息的函數
def send_line_message(message):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {CHANNEL_ACCESS_TOKEN}'
    }
    body = {
        'to': GROUP_ID,
        'messages': [{'type': 'text', 'text': message}]
    }
    response = requests.post(LINE_API_URL, headers=headers, json=body)
    if response.status_code != 200:
        logging.error(f"Failed to send message: {response.status_code} {response.text}")
    else:
        logging.info("Message sent successfully")

# 定義獲取數據並發送 LINE 消息的路由
@app.route('/send-data', methods=['GET'])
def send_data():
    targets = [
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?gw6UXnBQFxQcqRQvH_s-Zw&lang=traditional_chinese&time=0',
            'data_ids': ['lbl_online_date','lbl_daily_pw', 'lbl_today_price','lbl_total_price','lbl_system_time']
        },
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?9SGSfISfMFauB-qNFJwe2w&lang=traditional_chinese&time=',
            'data_ids': ['lbl_online_date','lbl_daily_pw', 'lbl_today_price','lbl_total_price','lbl_system_time']
        },
        {
            'url': 'http://tienching.ipvita.net/InstantPower.aspx?Us4azBhQh_643NPCj6EZzQ&lang=traditional_chinese&time=0',
            'data_ids': ['lbl_online_date','lbl_daily_pw', 'lbl_today_price','lbl_total_price','lbl_system_time']
        }
    ]

    messages = []
    for target in targets:
        data = scrape_data(target['url'], target['data_ids'])
        message = '\n'.join([f"{key}: {value}" for key, value in data.items()])
        messages.append(message)

    final_message = "\n\n".join(messages)
    send_line_message(final_message)

    return jsonify({'status': 'success', 'message': 'Data sent to LINE'})

# 配置 LINE webhook 路由
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_json()
    events = body.get('events', [])
    for event in events:
        if event['type'] == 'message' and event['message']['type'] == 'text':
            reply_token = event['replyToken']
            user_message = event['message']['text']
            if user_message == "抓取資料":
                send_data()
                send_line_message("資料已抓取並發送至群組")
            else:
                send_line_message("無效的指令")
    return 'OK'

if __name__ == '__main__':
    app.run(port=5000, debug=True)
