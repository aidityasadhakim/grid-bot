import ccxt, config, time, sys



exchange = ccxt.binance({
    "apiKey": config.API_KEY,
    "secret": config.API_SECURITY
})

ticker = exchange.fetch_ticker(config.SYMBOL)
start_price = float(ticker['bid'])
print("START PRICE : {}".format(start_price))
print("STOP LOSS At : {}".format(start_price * config.STOP_LOSS))

buy_orders = []
sell_orders = []

initial_buy_orders = exchange.create_market_buy_order(config.SYMBOL,config.POSITION_SIZE*config.NUM_SELL_GRID_LINES)
print(initial_buy_orders)

for i in range(config.NUM_BUY_GRID_LINES):
    price = ticker['bid'] - (ticker['bid'] * (config.GRID_SIZE * (i+1)))
    print("Submitting limit buy order at {}".format(price))
    order = exchange.create_limit_buy_order(config.SYMBOL,config.POSITION_SIZE,price,)
    buy_orders.append(order['info'])

for i in range(config.NUM_SELL_GRID_LINES):
    price = ticker['bid'] + (ticker['bid'] * (config.GRID_SIZE * (i+1)))
    print("Submitting limit sell order at {}".format(price))
    order = exchange.create_limit_sell_order(config.SYMBOL,config.POSITION_SIZE, price)
    sell_orders.append(order['info'])



while True:
    get_data = exchange.fetch_ticker(config.SYMBOL)
    price_tracker = float(get_data['bid'])
    closed_order_ids = []
    
    for buy_order in buy_orders:
        print("Checking buy orderr {}".format(buy_order['order_id']))

        try:
            order = exchange.fetchOrder(buy_order['order_id'],config.SYMBOL)
        except Exception as e:
            print("request failed, retrying")
            continue
        
        order_info = order['info']

        if order_info['status'] == config.CLOSED_ORDER_STATUS:
            closed_order_ids.append(order_info['order_id'])
            print("buy order executed at {}".format(order_info['price']))
            new_sell_price = float(order_info['price']) + (float(order_info['price']) * config.GRID_SIZE)
            print("create a new sell order at {}".format(new_sell_price))
            new_sell_order = exchange.create_limit_sell_order(config.SYMBOL, config.POSITION_SIZE, new_sell_price)
            sell_orders.append(new_sell_order['info'])
        
        time.sleep(config.CHECK_ORDERS_FREQUENCY)

    for sell_order in sell_orders:
        print("Checking sell order {}".format(sell_order['order_id']))

        try:
            order = exchange.fetchOrder(sell_order['order_id'],config.SYMBOL)
        except Exception as e:
            print("request failed, retrying")
            continue
        
        order_info = order['info']

        if order_info['status'] == config.CLOSED_ORDER_STATUS:
            closed_order_ids.append(order_info['order_id'])
            print("sell order executed at {}".format(order_info['price']))
            new_buy_price = float(order_info['price']) - (float(order_info['price']) * config.GRID_SIZE)
            print("create a new buy order at {}".format(new_buy_price))
            new_buy_order = exchange.create_limit_buy_order(config.SYMBOL, config.POSITION_SIZE, new_buy_price)
            buy_orders.append(new_buy_order['info'])
        
        time.sleep(config.CHECK_ORDERS_FREQUENCY)
    
    for order_id in closed_order_ids:
        buy_orders = [buy_order for buy_order in buy_orders if buy_order['order_id'] != order_id]
        sell_orders = [sell_order for sell_order in sell_orders if sell_order['order_id'] != order_id]

    if len(sell_order) == 0:
        sys.exit("Nothing to sell, bot stopped")

    if(price_tracker < (start_price * config.STOP_LOSS)):
        print("Price Hitting The Stop Loss..")
        print("Cancelling All Order")
        exchange.cancel_all_orders(config.SYMBOL)
        print("Keep Selling Until No More Free Asset Left")
        while True:
            try:
                exchange.create_market_sell_order(config.SYMBOL,config.POSITION_SIZE*5)
            except Exception as e:
                print("You hit the stop loss, all the asset has been sold!")
                break