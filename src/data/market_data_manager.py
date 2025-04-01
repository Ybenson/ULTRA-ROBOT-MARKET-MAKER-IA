"""
Market Data Manager module for handling market data operations.
"""
from typing import Dict, List, Optional
import ccxt
import pandas as pd
from loguru import logger

class MarketDataManager:
    """
    Manages market data operations including fetching, processing, and storing market data.
    """
    
    def __init__(self, exchange_id: str = 'binance', symbol: str = 'BTC/USDT'):
        """
        Initialize the MarketDataManager.
        
        Args:
            exchange_id (str): The ID of the exchange to use (default: 'binance')
            symbol (str): The trading pair symbol (default: 'BTC/USDT')
        """
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.exchange = getattr(ccxt, exchange_id)()
        logger.info(f"Initialized MarketDataManager for {exchange_id} - {symbol}")
        
    def fetch_ohlcv(self, timeframe: str = '1m', limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data.
        
        Args:
            timeframe (str): The timeframe for the data (default: '1m')
            limit (int): Number of candles to fetch (default: 100)
            
        Returns:
            pd.DataFrame: OHLCV data in a pandas DataFrame
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            logger.info(f"Fetched {len(df)} OHLCV records")
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV data: {str(e)}")
            raise
            
    def fetch_order_book(self, limit: int = 20) -> Dict:
        """
        Fetch the current order book.
        
        Args:
            limit (int): Depth of the order book to fetch (default: 20)
            
        Returns:
            Dict: Order book data containing bids and asks
        """
        try:
            order_book = self.exchange.fetch_order_book(self.symbol, limit)
            logger.info(f"Fetched order book with {len(order_book['bids'])} bids and {len(order_book['asks'])} asks")
            return order_book
        except Exception as e:
            logger.error(f"Error fetching order book: {str(e)}")
            raise
            
    def fetch_ticker(self) -> Dict:
        """
        Fetch the current ticker information.
        
        Returns:
            Dict: Current ticker information
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            logger.info(f"Fetched ticker for {self.symbol}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker: {str(e)}")
            raise
