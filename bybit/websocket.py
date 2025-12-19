import websocket,json,threading,time,logging
prices={}
last_update = 0

# Set up custom logging with file details
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

# Create formatter with file details in brackets
formatter = logging.Formatter('[%(filename)s:%(lineno)d] %(levelname)s: %(message)s')
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)

def on_message(ws,msg):
    global last_update
    data=json.loads(msg)
    if "data" in data:
        for d in data["data"]:
            prices[d["symbol"]]=float(d["lastPrice"])
        last_update = time.time()
        # Log every 60 seconds
        if time.time() - last_update > 60:
            logger.info(f"📡 WebSocket updated {len(prices)} prices")

def start_ws(symbols):
    args=[f"tickers.{s}" for s in symbols]
    def run():
        ws=websocket.WebSocketApp("wss://stream.bybit.com/v5/public/linear",on_message=on_message)
        ws.on_open=lambda ws: ws.send(json.dumps({"op":"subscribe","args":args}))
        ws.run_forever()
    threading.Thread(target=run,daemon=True).start()
