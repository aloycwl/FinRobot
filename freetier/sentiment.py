# import requests
# import pandas as pd

# API_KEY = 'jyqdin0qf8tnspz8iwc949zmgm96psmxv89y7wta'
# symbol = 'BTC'

# url = f'https://lunarcrush.com/v4?data=assets&key={API_KEY}&symbol={symbol}'

# response = requests.get(url)
# data = response.json()

# btc_sentiment = data['data'][0]
# print(btc_sentiment['galaxy_score'], btc_sentiment['alt_rank'], btc_sentiment['social_score'])


import requests

url = "https://lunarcrush.com/api4/public/coins/list/v2"
headers = {
  'Authorization': 'Bearer jyqdin0qf8tnspz8iwc949zmgm96psmxv89y7wta'
}

response = requests.request("GET", url, headers=headers)

print(response.text.encode('utf8'))
