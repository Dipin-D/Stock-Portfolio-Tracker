from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth import authenticate
from django.contrib import messages
import yfinance as yf
from django.contrib.auth.decorators import login_required
from .models import Portfolio
from django.contrib.auth.forms import UserCreationForm
from .utils import download_n_clean_data

def front_view(request):
    return render(request, 'front.html')
def backtest_view(request):
# Set the symbol and date range
    symbol = 'SPY'
    start_date = '1993-01-01'
    end_date = '2020-02-16'
    
    # Get the cleaned data
    clean_data = download_n_clean_data(symbol, start_date, end_date)

    # Pass the data to the template
    context = {'data': clean_data.to_dict(orient='records')}  # Convert DataFrame to a dictionary

    # Pass the data to the template
    return render(request, 'backtest.html', context)
# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('portfolio')  
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'login.html')

# Logout view
def logout_view(request):
    logout(request)
    return redirect('login')  

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()  
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')  
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def portfolio_view(request):
    user_portfolio = Portfolio.objects.filter(user=request.user)
    portfolio_data = []
    total_value = 0

    for item in user_portfolio:
        stock_data = yf.Ticker(item.symbol).history(period="1d")
        current_price = stock_data['Close'].iloc[0]  
        stock_value = current_price * item.quantity
        portfolio_data.append({
            'symbol': item.symbol,
            'quantity': item.quantity,
            'current_price': current_price,
            'stock_value': stock_value,
        })
        total_value += stock_value

    return render(request, 'portfolio.html', {'portfolio_data': portfolio_data, 'total_value': total_value})
