from ast import Num
from glob import glob
from itertools import count
from tkinter import LAST
from flask import Flask, render_template, jsonify, request
import ccxt, config, sys, time, threading

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

GRID_LINES = {}

buy_orders = []
sell_orders = []

app = Flask(__name__)

exchange = ccxt.binance({
    "apiKey": config.API_KEY,
    "secret": config.API_SECURITY
})

START_PRICES = 0
LAST_PRICES = 0

@app.route('/')
def index():
    get_Balances = exchange.fetchBalance()
    balances_Info = get_Balances['info']['balances']
    len_balances = len(balances_Info)
    return render_template('index.html', balances_Info = balances_Info, len_balances = len_balances)

@app.route('/start', methods=['POST'])
def start():
    global BAR_DETAIL

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

    message = False
    if(percentage_size < 0.0005):
        message = True
        print(message)

    BAR_DETAIL['min_notional'] = BAR_DETAIL['total_grid']*2

    return render_template('start.html', bar_detail = BAR_DETAIL, message=message, percentage=round(percentage_size,4))

def get_grid_lines():
    global BAR_DETAIL
    global GRID_LINES

    DIFFERENCE = BAR_DETAIL['high_bar'] - BAR_DETAIL['low_bar']

    # Get Total Sell Bar, taking it from the position of the current price by percentage
    # Getting the current price
    current_price = exchange.fetch_ticker(BAR_DETAIL['symbol'])
    current_price = float(current_price['bid'])

    # Getting the distance from current price to high bar
    CURRENT_PRICE_DISTANCE = ((current_price - BAR_DETAIL['low_bar']) / DIFFERENCE * 100)
    print(DIFFERENCE)
    print(CURRENT_PRICE_DISTANCE)

    # Getting the total sell bar by dividing the distance with the grid 
    NUM_SELL_GRID = (((100 - CURRENT_PRICE_DISTANCE) / 100) * BAR_DETAIL['total_grid'] )
    NUM_SELL_GRID = int(NUM_SELL_GRID)
    # Getting the total buy bar by dividing the distance with the grid size without substracting with 100

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

    BAR_DETAIL['notional'] = float(notional)

    ticker = exchange.fetch_ticker(BAR_DETAIL['symbol'])
    START_PRICES = ticker['bid']

    # Get Total Amount for each grid
    AMOUNT_GRID = BAR_DETAIL['notional'] / (BAR_DETAIL['total_grid'] - 1)
    BAR_DETAIL['amount'] = AMOUNT_GRID / START_PRICES
    # BAR_DETAIL['grid_size'] = BAR_DETAIL['grid_size'] / 100

    # Create market order specified to the number of total sell grid lines
    initial_buy_orders = exchange.create_market_buy_order(BAR_DETAIL['symbol'], BAR_DETAIL['amount'] * (GRID_LINES['num_sell']))
    print(initial_buy_orders)

    for i in range(GRID_LINES['num_buy']):
        price = ticker['bid'] - (BAR_DETAIL['grid_size'] * (i+1))
        print("Submitting limit buy order at {}".format(price))
        order = exchange.create_limit_buy_order(BAR_DETAIL['symbol'],BAR_DETAIL['amount'],price)
        buy_orders.append(order['info'])
    order = exchange.fetchOrder(buy_orders[-1]['orderId'],BAR_DETAIL['symbol'])
    LAST_PRICES = order['price']

    for i in range(GRID_LINES['num_sell']):
        price = ticker['bid'] + (BAR_DETAIL['grid_size'] * (i+1))
        print("Submitting limit sell order at {}".format(price))
        order = exchange.create_limit_sell_order(BAR_DETAIL['symbol'],BAR_DETAIL['amount'],price)
        sell_orders.append(order['info'])



@app.route('/run', methods=['POST'])
def run():
    # global count

    global BAR_DETAIL

    # Taking the FORM Detail, so the page is accessable even if the owner already close it
    FORM_DETAIL = {}
    FORM_DETAIL['symbol'] = request.form['symbol']
    FORM_DETAIL['high_bar'] = float(request.form['high_bar'])
    FORM_DETAIL['low_bar'] = float(request.form['low_bar'])
    FORM_DETAIL['total_grid'] = float(request.form['total_grid'])
    FORM_DETAIL['min_notional'] = float(FORM_DETAIL['total_grid'])*2

    
    difference = FORM_DETAIL['high_bar'] - FORM_DETAIL['low_bar']

    FORM_DETAIL['grid_size'] = difference / FORM_DETAIL['total_grid']

    global GRID_LINES

    # Get the Number of Total Grid Lines
    get_grid_lines()

    # Making Initial Buy
    initial_buy(request.form['notional'])

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

            # Getting the order data by id
            try:
                order = exchange.fetchOrder(buy_order['orderId'],BAR_DETAIL['symbol'])
            except Exception as e:
                print("request failed, retrying")
                continue
            
            order_info = order['info']

            # If the buy order is closed than a new sell order will be created
            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                closed_order_ids.append(order_info['orderId'])
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

            if order_info['status'] == config.CLOSED_ORDER_STATUS:
                closed_order_ids.append(order_info['orderId'])
                print("sell order executed at {}".format(order_info['price']))
                new_buy_price = float(order_info['price']) - BAR_DETAIL['grid_size']
                print("create a new buy order at {}".format(new_buy_price))
                new_buy_order = exchange.create_limit_buy_order(BAR_DETAIL['symbol'], BAR_DETAIL['amount'], new_buy_price)
                buy_orders.append(new_buy_order['info'])
            
            time.sleep(config.CHECK_ORDERS_FREQUENCY)
        
        for order_id in closed_order_ids:
            buy_orders = [buy_orders for buy_order in buy_orders if buy_order['orderId'] != order_id]
            sell_orders = [sell_orders for sell_order in sell_orders if sell_order['orderId'] != order_id]

        if len(sell_orders) == 0:
            sys.exit("Nothing to sell, bot stopped")

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

def run_app():
    app.run(debug=False, threaded=True)

if __name__ == "__main__":
    first_thread = threading.Thread(target=run_app)
    first_thread.start()

# start_price = exchange.fetch_ticker(config.SYMBOL)
# start_price = float(start_price['bid'])


# print("Start Price  : {}".format(start_price))
# print("End Price  : {}".format(start_price * 0.9995))
# print("End Price  : {}".format(start_price * 1.0005))



# try:
#     # exchange.create_market_sell_order(config.SYMBOL,config.POSITION_SIZE)
#     order = exchange.create_limit_buy_order(config.SYMBOL,config.POSITION_SIZE,start_price * 0.99)
#     print(order)
# except Exception as e:
#     print(e)
    
