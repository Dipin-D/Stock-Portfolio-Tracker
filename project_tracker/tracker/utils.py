import yfinance as yf
import pandas as pd

def download_n_clean_data(symbol, start_date, end_date):
    """
    Downloads and cleans historical stock data for a given symbol and date range.

    Parameters:
        symbol (str): Stock symbol (default is 'SPY').
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.

    Returns:
        pd.DataFrame: Cleaned stock data.
    """
    # Download SPY data
    data = yf.download(symbol, start=start_date, end=end_date)
    
    # Get Rid of ticker columnn
    if isinstance(data.columns, pd.MultiIndex):
        # Flatten the MultiIndex by using the second level as column names
        data.columns = data.columns.get_level_values(0)
        
    # Resetting the index (so that date column has its own index)
    data.reset_index(inplace=True)
    
    # Reorder the columns to match the desired order
    data = data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

    #data['Date'] = pd.to_datetime(data['Date'])

    # Convert 'Date' column to Unix timestamp (replace 'Date' column with Unix timestamp)
    data['Date'] = data['Date'].apply(lambda x: x.timestamp())

    return data