import websocket,json,threading,time,logging
prices={}
last_update = 0
last_log = 0
# Bybit's tickers feed pushes on nearly every trade; skip re-processing a
# symbol faster than this to cut CPU spent on a value only read every few minutes
MIN_UPDATE_INTERVAL = 1.0
_last_symbol_update = {}

logger = logging.getLogger(__name__)

def on_message(ws,msg):
    global last_update, last_log
    try:
        data=json.loads(msg)
        if isinstance(data, dict) and "data" in data:
            now = time.time()
            for d in data["data"]:
                symbol = d.get("symbol")
                if symbol and "lastPrice" in d and now - _last_symbol_update.get(symbol, 0) >= MIN_UPDATE_INTERVAL:
                    prices[symbol]=float(d["lastPrice"])
                    _last_symbol_update[symbol] = now
            last_update = now
            if now - last_log > 60:
                logger.info(f"📡 WebSocket updated {len(prices)} prices")
                last_log = now
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {e}")

def start_ws(symbols):
    args=[f"tickers.{s}" for s in symbols]
    def run():
        ws=websocket.WebSocketApp("wss://stream.bybit.com/v5/public/linear",on_message=on_message)
        ws.on_open=lambda ws: ws.send(json.dumps({"op":"subscribe","args":args}))
        ws.run_forever()
    threading.Thread(target=run,daemon=True).start()
