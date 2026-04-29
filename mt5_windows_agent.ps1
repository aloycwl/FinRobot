# MT5 Windows Execution Agent
# Run this on your Windows machine. This is the ONLY thing you need to run on Windows.
# Install requirements first: pip install MetaTrader5 flask requests

import json
import MetaTrader5 as mt5
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/place_order', methods=['POST'])
def place_order():
    data = request.json
    
    if not mt5.initialize():
        return jsonify({"success": False, "error": "MT5 initialize failed"}), 500
        
    symbol = data['symbol']
    side = data['side']
    lot = data['lot']
    deviation = data.get('deviation', 20)
    
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return jsonify({"success": False, "error": "Symbol not found"}), 400
        
    order_type = mt5.ORDER_TYPE_BUY if side.lower() == "buy" else mt5.ORDER_TYPE_SELL
    price = tick.ask if side.lower() == "buy" else tick.bid
    
    request_params = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": 20260428,
        "comment": "finrobot-auto",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request_params)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return jsonify({"success": False, "error": f"Order failed: {result.retcode}"}), 400
        
    return jsonify({
        "success": True,
        "ticket": result.order,
        "price": result.price,
        "volume": result.volume
    })


if __name__ == '__main__':
    print("✅ MT5 Windows Agent running on port 8642")
    print("   Run this on your Windows machine with MT5 opened and logged in")
    print("   Linux daemon will send orders here automatically")
    app.run(host='0.0.0.0', port=8642)
