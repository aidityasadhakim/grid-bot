# Created by Aidityas Adhakim
# This code is not fully mine
# You can watch the explanation of the main algorithm in the link below
# https://youtu.be/QzqMGX4Qk1A

from flask import Flask, render_template, request
import ccxt, config, sys, time, threading

# This will contain all the detail for the grid lines bar
BAR_DETAIL = {
        'symbol':"",
        'high_bar':0,
        'low_bar':0,
        'total_grid':0,
        'grid_size':0,
        'min_notional':0,
        'notional':0,
        'amount':0
    }

# This will contain the grid lines detail
GRID_LINES = {}

# This will contain the order id, so that we can track an open order
buy_orders = []
sell_orders = []

app = Flask(__name__)

# You can change the exchanges to whatever you want
exchange = ccxt.binance({
    "apiKey": config.API_KEY,
    "secret": config.API_SECURITY
})

# Track the start price and the last buy order or the bottom price of the bar
START_PRICES = 0
LAST_PRICES = 0

# Index page where you can choose what coin to trade
# Also to input the total bar
# And you can also put the price boundary
@app.route('/')
def index():
    get_Balances = exchange.fetchBalance()
    balances_Info = get_Balances['info']['balances']
    len_balances = len(balances_Info)
    return render_template('index.html', balances_Info = balances_Info, len_balances = len_balances)

# This page will show you all the information you have input
# and also shows the size of each bar
# It also show the percentage profit of each bar
@app.route('/start', methods=['POST'])
def start():
    global BAR_DETAIL

    # Fill the bar detail information based on the data sent
    BAR_DETAIL['symbol'] = request.form['symbol']
    BAR_DETAIL['high_bar'] = float(request.form['high_bar'])
    BAR_DETAIL['low_bar'] = float(request.form['low_bar'])
    BAR_DETAIL['total_grid'] = float(request.form['grid'])

    # Getting price data to get the percentage rise in every bar to avoid loss from fee
    price = exchange.fetch_ticker(BAR_DETAIL['symbol'])
    price = float(price['bid'])

    # Counting the percentage distance from each bar
    difference = BAR_DETAIL['high_bar'] -BAR_DETAIL['low_bar']
    BAR_DETAIL['grid_size'] = (difference / BAR_DETAIL['total_grid'])
    percentage_size = BAR_DETAIL['grid_size'] / price 

    # The fee for binance is 0.05%
    # so if the percentage profit is below that than you will gain no profit
    # this will show up to alert you, if your percentage profit is negative
    message = False
    if(percentage_size < 0.0005):
        message = True
        print(message)

    # This is for the minimum notional for each trade/bar
    # note that in Binance the min notional is $10
    # so if you wanted to have 10 grid you need min notional of $100
    BAR_DETAIL['min_notional'] = BAR_DETAIL['total_grid']*10

    return render_template('start.html', bar_detail = BAR_DETAIL, message=message, percentage=round(percentage_size,4))

def get_grid_lines():
    global BAR_DETAIL
    global GRID_LINES

    # Get the difference price from the highest bar to the lowest bar
    DIFFERENCE = BAR_DETAIL['high_bar'] - BAR_DETAIL['low_bar']

    # Get Total Sell Bar, taking it from the position of the current price by percentage
    # Getting the current price
    current_price = exchange.fetch_ticker(BAR_DETAIL['symbol'])
    current_price = float(current_price['bid'])

    # Getting the distance from current price to high bar
    CURRENT_PRICE_DISTANCE = ((current_price - BAR_DETAIL['low_bar']) / DIFFERENCE * 100)

    # Getting the total sell bar from its current position
    NUM_SELL_GRID = (((100 - CURRENT_PRICE_DISTANCE) / 100) * BAR_DETAIL['total_grid'] )
    NUM_SELL_GRID = int(NUM_SELL_GRID)

    # Getting the total buy bar from its current position
    NUM_BUY_GRID = int(((CURRENT_PRICE_DISTANCE/100) * BAR_DETAIL['total_grid']))

    GRID_LINES = {
        "num_sell":NUM_SELL_GRID,
        "num_buy":NUM_BUY_GRID
    }

def initial_buy(notional):
    global BAR_DETAIL
    global GRID_LINES
    global START_PRICES
    global LAST_PRICES

    # Getting the notional that will be traded
    BAR_DETAIL['notional'] = float(notional)

    # Getting the start prices
    ticker = exchange.fetch_ticker(BAR_DETAIL['symbol'])
    START_PRICES = ticker['bid']

    # Get Total Amount for each grid
    AMOUNT_GRID = BAR_DETAIL['notional'] / (BAR_DETAIL['total_grid'] - 1)
    BAR_DETAIL['amount'] = AMOUNT_GRID / START_PRICES
    # BAR_DETAIL['grid_size'] = BAR_DETAIL['grid_size'] / 100

    # Create market order specified to the number of total sell grid lines
    initial_buy_orders = exchange.create_market_buy_order(BAR_DETAIL['symbol'], BAR_DETAIL['amount'] * (GRID_LINES['num_sell']))
    print(initial_buy_orders)

    # This will create a limit buy order based on the total of buy grid lines
    # Note that every bar is decremental by the grid size
    for i in range(GRID_LINES['num_buy']):
        price = ticker['bid'] - (BAR_DETAIL['grid_size'] * (i+1))
        print("Submitting limit buy order at {}".format(price))
        order = exchange.create_limit_buy_order(BAR_DETAIL['symbol'],BAR_DETAIL['amount'],price)
        buy_orders.append(order['info'])
    last_order = exchange.fetchOrder(buy_orders[-1]['orderId'],BAR_DETAIL['symbol'])
    LAST_PRICES = last_order['price']

    # This will create a limit sell order based on the total of sell grid lines
    # Note that every bar is incremental by the grid size
    for i in range(GRID_LINES['num_sell']):
        price = ticker['bid'] + (BAR_DETAIL['grid_size'] * (i+1))
        print("Submitting limit sell order at {}".format(price))
        order = exchange.create_limit_sell_order(BAR_DETAIL['symbol'],BAR_DETAIL['amount'],price)
        sell_orders.append(order['info'])



@app.route('/run', methods=['POST'])
def run():
    global BAR_DETAIL
    global GRID_LINES


    # Taking the FORM Detail, so the page is accessable even if the owner already close it
    FORM_DETAIL = {}
    FORM_DETAIL['symbol'] = request.form['symbol']
    FORM_DETAIL['high_bar'] = float(request.form['high_bar'])
    FORM_DETAIL['low_bar'] = float(request.form['low_bar'])
    FORM_DETAIL['total_grid'] = float(request.form['total_grid'])
    FORM_DETAIL['min_notional'] = float(FORM_DETAIL['total_grid'])*2

    # Calculate the difference from highest bar to lowest bar
    difference = FORM_DETAIL['high_bar'] - FORM_DETAIL['low_bar']

    FORM_DETAIL['grid_size'] = difference / FORM_DETAIL['total_grid']


    # Get the Number of Total Grid Lines
    get_grid_lines()

    # Making Initial Buy
    initial_buy(request.form['notional'])

    # Running a multithread
    # This will run an Infinite Loop where the infinite loop will keep checking the order
    # Check the detail on while_function function
    first_thread = threading.Thread(target=while_function)
    first_thread.start()
    
    return render_template(
                            'running.html', 
                            bar_detail = FORM_DETAIL,
                            notional = request.form['notional'],
                            grid_lines = GRID_LINES,
                            amount = BAR_DETAIL['amount']
                            )

def while_function():
    # Submitting the global variable
    global buy_orders 
    global sell_orders
    global BAR_DETAIL
    global GRID_LINES
    global START_PRICES
    global LAST_PRICES

    # Start To Run the grid trading strategy
    while True:
        # Get the pair data and tracking price movement
        get_data = exchange.fetch_ticker(BAR_DETAIL['symbol'])
        price_tracker = float(get_data['bid'])

        # tracking the closed order
        closed_order_ids = []
        
        # Tracking the buy order
        for buy_order in buy_orders:
            print("Checking buy orderr {}".format(buy_order['orderId']))

            # Getting the buy order by id
            try:
                order = exchange.fetchOrder(buy_order['orderId'],BAR_DETAIL['symbol'])
            except Exception as e:
                print("request failed, retrying")
                continue
            
            order_info = order['info']

            # If the buy order is closed than a new sell order will be created
            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                # Appending the closed order to closed_order_ids
                closed_order_ids.append(order_info['orderId'])

                # Creating a new sell order
                print("buy order executed at {}".format(order_info['price']))
                new_sell_price = float(order_info['price']) + BAR_DETAIL['grid_size']
                print("create a new sell order at {}".format(new_sell_price))
                new_sell_order = exchange.create_limit_sell_order(BAR_DETAIL['symbol'], BAR_DETAIL['amount'], new_sell_price)
                sell_orders.append(new_sell_order['info'])
            
            time.sleep(config.CHECK_ORDERS_FREQUENCY)

        for sell_order in sell_orders:
            print("Checking sell order {}".format(sell_order['orderId']))

            # Checking the sell order by id
            try:
                order = exchange.fetchOrder(sell_order['orderId'],BAR_DETAIL['symbol'])
            except Exception as e:
                print("request failed, retrying")
                continue
            
            order_info = order['info']

            # If the buy order is closed than a new sell order will be created
            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                # Append the closed order to closed_order_ids list
                closed_order_ids.append(order_info['orderId'])

                # Creating a new sell order
                print("sell order executed at {}".format(order_info['price']))
                new_buy_price = float(order_info['price']) - BAR_DETAIL['grid_size']
                print("create a new buy order at {}".format(new_buy_price))
                new_buy_order = exchange.create_limit_buy_order(BAR_DETAIL['symbol'], BAR_DETAIL['amount'], new_buy_price)
                buy_orders.append(new_buy_order['info'])
            
            time.sleep(config.CHECK_ORDERS_FREQUENCY)
        
        # This will check for every order than has been closed
        # And later it will remove it from the main order list
        # Then later the system will not check for the closed order anymore
        for order_id in closed_order_ids:
            buy_orders = [buy_orders for buy_order in buy_orders if buy_order['orderId'] != order_id]
            sell_orders = [sell_orders for sell_order in sell_orders if sell_order['orderId'] != order_id]

        # This will get the real time price data
        # And if the price go below the stop loss
        # The bot will automatically close all order and keep selling the coin until no more left
        if(price_tracker < (LAST_PRICES * config.STOP_LOSS)):
            print("Price Hitting The Stop Loss..")
            print("Cancelling All Order")
            exchange.cancel_all_orders(BAR_DETAIL['symbol'])
            print("Keep Selling Until No More Free Asset Left")
            while True:
                try:
                    exchange.create_market_sell_order(BAR_DETAIL['symbol'],BAR_DETAIL['amount']*5)
                except Exception as e:
                    print("You hit the stop loss, all the asset has been sold!")
                    sys.exit("Bot Stopped")

# This will run the app
def run_app():
    app.run(debug=False, threaded=True)

# This will start the app
if __name__ == "__main__":
    first_thread = threading.Thread(target=run_app)
    first_thread.start()