import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json

import os


def scrape_data(url, stockgroup):
    # Send HTTP request to get the page content
    response = requests.get(url,headers={'User-Agent': 'Mozilla/5.0'})

    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, "lxml")
        
        # Find the table with the Dow 30 components
        table = soup.find('table', {'class': 'table table-hover table-borderless table-sm'})

        #convert beautiful soup objects to string and parse to panda
        pulled_df = pd.read_html(str(table))[0]

        # Access a specific column by its name
        column_data = pulled_df[['Company','Symbol']]

        my_dict1 = {}

        list_st = []
        my_dict1[stockgroup] = list_st

        for index, row in column_data.iterrows():
            my_dict2= {}
            company = row['Company']
            symbol = row['Symbol']
            my_dict2['name'] = company
            my_dict2['symbol'] = symbol

            list_st.append(my_dict2)
        
        current_directory = os.getcwd()
        filepath = os.path.join(current_directory, 'tracker', 'static', 'data')
        full_path = os.path.join(filepath, f"{stockgroup}.json")

        # Ensure the directory exists
        os.makedirs(filepath, exist_ok=True)

        # Write JSON data to the file
        with open(full_path, 'w') as json_file:
            json.dump(my_dict1, json_file, indent=4)
    return






dow_30_url= 'https://www.slickcharts.com/dowjones'
scrape_data(dow_30_url, 'Dow Jones 30')

nasdaq_100_url = 'https://www.slickcharts.com/nasdaq100' 
scrape_data(nasdaq_100_url, 'Nasdaq 100')

snp_500_url = 'https://www.slickcharts.com/sp500'
scrape_data(snp_500_url, 'S&P 500')
