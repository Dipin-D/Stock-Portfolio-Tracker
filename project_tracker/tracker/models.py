from django.db import models
from django.contrib.auth.models import User

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)  
    quantity = models.IntegerField()          

    def __str__(self):
        return f'{self.symbol} ({self.quantity} shares)'
