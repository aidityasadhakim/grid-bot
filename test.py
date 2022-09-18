from flask import Flask, render_template, jsonify, request
import ccxt, config, sys, time, threading

app = Flask(__name__)

exchange = ccxt.binance({
    "apiKey": config.API_KEY,
    "secret": config.API_SECURITY
})

data = exchange.fetch_ticker('ETHUSDT')
data = data['bid']
print(data)