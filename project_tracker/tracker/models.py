from django.db import models
from django.contrib.auth.models import User
import yfinance as yf

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)  
    quantity = models.IntegerField()          

    def __str__(self):
        return f'{self.symbol} ({self.quantity} shares)'

class Stock_Group(models.Model):
    name = models.CharField(max_length=100)  # e.g., Dow30, S&P500, etc

class Stock(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    sector = models.CharField(max_length=10)

    # Many-to-many relationship with StockGroup
    groups = models.ManyToManyField(Stock_Group, related_name="stocks")

