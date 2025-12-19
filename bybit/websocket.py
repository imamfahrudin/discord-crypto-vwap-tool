import websocket,json,threading
prices={}
def on_message(ws,msg):
    data=json.loads(msg)
    if "data" in data:
        for d in data["data"]:
            prices[d["symbol"]]=float(d["lastPrice"])

def start_ws(symbols):
    args=[f"tickers.{s}" for s in symbols]
    def run():
        ws=websocket.WebSocketApp("wss://stream.bybit.com/v5/public/linear",on_message=on_message)
        ws.on_open=lambda ws: ws.send(json.dumps({"op":"subscribe","args":args}))
        ws.run_forever()
    threading.Thread(target=run,daemon=True).start()
