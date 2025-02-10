from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth import authenticate
from django.contrib import messages
from .utils import download_n_clean_data
from django.http import JsonResponse
from .models import Stock

import yfinance as yf
<<<<<<< HEAD
from django.contrib.auth.decorators import login_required
from .models import Portfolio
from django.contrib.auth.forms import UserCreationForm
from .utils import download_n_clean_data
=======
from .models import Portfolio
from django.contrib.auth.forms import UserCreationForm
from .utils import download_n_clean_data
import plotly.express as px
import plotly.io as pio
>>>>>>> 56c9d25 (Portfolio Basic update)

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
    
def fetch_stock_data(request):
    ticker = request.GET.get('ticker', 'SPY').upper()
    start_date = request.GET.get('start_date', '1993-01-01')
    end_date = request.GET.get('end_date', '2020-02-16')


    #### checks input data against models database
    if not Stock.objects.filter(symbol=ticker).exists():
        return JsonResponse({
            'valid': False,
            'error': f'Ticker {ticker} not found in database'
        }, status=200)
    

    try:
        # Use your existing utility function
        clean_data = download_n_clean_data(ticker, start_date, end_date)
        
        # Convert timestamp back to datetime for frontend
       
        return JsonResponse({
            'valid': True,
            'data': clean_data.to_dict(orient='records')
            
        })
    
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'error': str(e)
        }, status=200)
    
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

<<<<<<< HEAD
def portfolio_view(request):
    user_portfolio = Portfolio.objects.filter(user=request.user)
    portfolio_data = []
    total_value = 0

=======

def portfolio_view(request): 
    user_portfolio = Portfolio.objects.filter(user=request.user)
    portfolio_data = []
    total_value = 0
    stock_labels = []
    stock_values = []

    # Collect stock data and calculate total portfolio value
>>>>>>> 56c9d25 (Portfolio Basic update)
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
<<<<<<< HEAD

    return render(request, 'portfolio.html', {'portfolio_data': portfolio_data, 'total_value': total_value})
=======
        stock_labels.append(item.symbol)
        stock_values.append(stock_value)

    # Handle POST request for adding funds and allocating to SPY and AAPL
    if request.method == "POST":
        try:
            amount = float(request.POST.get("amount"))
            if amount <= 0:
                messages.error(request, "Enter a valid amount.")
                return redirect("portfolio")

            # Fetch latest prices for SPY and AAPL
            symbols = ["SPY", "AAPL"]
            prices = {symbol: yf.Ticker(symbol).history(period="1d")['Close'].iloc[0] for symbol in symbols}

            # Allocate money equally
            investment_per_stock = amount / 2
            quantities = {symbol: investment_per_stock / prices[symbol] for symbol in symbols}

            # Update Portfolio
            for symbol, quantity in quantities.items():
                portfolio_item, created = Portfolio.objects.get_or_create(user=request.user, symbol=symbol, defaults={'quantity': 0})
                portfolio_item.quantity += quantity
                portfolio_item.save()

            messages.success(request, "Funds allocated successfully!")
            return redirect("portfolio")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect("portfolio")

    # Create a Plotly Pie Chart
    pie_chart = None
    if total_value > 0:
        fig = px.pie(
            names=stock_labels, 
            values=stock_values, 
            title="Portfolio Allocation", 
            hole=0.3
        )
        pie_chart = pio.to_html(fig, full_html=False)

    return render(request, 'portfolio.html', {
        'portfolio_data': portfolio_data, 
        'total_value': total_value,
        'pie_chart': pie_chart  # Send chart to template
    })


>>>>>>> 56c9d25 (Portfolio Basic update)
def stock_list(request, group_name):
    group = Stock_Group.objects.get(name=group_name)
    stocks = group.stocks.all()
    return render(request, 'pro_scan.html', {'stocks': stocks})
