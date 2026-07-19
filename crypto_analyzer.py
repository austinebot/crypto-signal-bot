import requests
import statistics
import os
import time
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}

def fetch_candles(symbol, interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        time.sleep(3)  # Délai important
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        candles = []
        for c in raw:
            try:
                candles.append({
                    'open': float(c[1]),
                    'high': float(c[2]),
                    'low': float(c[3]),
                    'close': float(c[4])
                })
            except:
                continue
        return candles
    except Exception as e:
        print(f"API error for {symbol}: {e}")
        return []

# (Le reste du code est identique à la version précédente)

def build_analysis(symbol):
    candles15 = fetch_candles(symbol)
    if not candles15:
        return {"symbol": symbol, "signal": "WAIT", "error": "No data"}

    closes15 = [c['close'] for c in candles15]
    price = closes15[-1]

    trend15 = "haussière" if ema(closes15,20)[-1] > ema(closes15,50)[-1] and price > ema(closes15,20)[-1] else "baissière" if ema(closes15,20)[-1] < ema(closes15,50)[-1] and price < ema(closes15,20)[-1] else "indécise"
    rsi_val = rsi(closes15)
    adx = compute_adx(candles15)
    macd_hist, macd_prev = compute_macd(closes15)
    support, resistance = find_s_r(candles15)
    pattern = detect_pattern(candles15)

    signal = "WAIT"
    confidence = 55
    reasons = [f"Pattern: {pattern}"]

    if trend15 == "haussière" and rsi_val < 68 and adx > 23 and macd_hist > macd_prev:
        signal = "BUY"
        confidence += 45
        reasons.append("Alignement haussier + momentum")
    elif trend15 == "baissière" and rsi_val > 32 and adx > 23 and macd_hist < macd_prev:
        signal = "SELL"
        confidence += 45
        reasons.append("Alignement baissier + momentum")

    if "Double Bottom" in pattern or "Double Top" in pattern:
        confidence += 12

    if signal != "WAIT":
        sl = support * 0.996 if signal == "BUY" else resistance * 1.004
        tp = resistance if signal == "BUY" else support
        rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
        if rr < 2.3:
            signal = "WAIT"
        else:
            confidence += 10

    if adx < 20 or confidence < 72:
        signal = "WAIT"

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "signal": signal,
        "confidence": min(confidence, 95),
        "pattern": pattern,
        "trend15": trend15,
        "rsi": round(rsi_val, 1),
        "adx": round(adx, 1),
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "rr": round(rr, 2) if 'rr' in locals() else None,
        "time": datetime.utcnow().strftime("%H:%M UTC")
    }

# CONFIGURATION
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(result):
    if result["signal"] == "WAIT":
        return
    msg = f"""🚨 <b>{result['signal']}</b> — {result['confidence']}% 

{result['symbol']} @ {result['price']}
Pattern : {result['pattern']}
T15m : {result['trend15']}
RSI : {result['rsi']} | ADX : {result['adx']}
Support : {result['support']} | Rés : {result['resistance']}
R:R ≈ 1:{result['rr']}
"""
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"})

if __name__ == "__main__":
    for symbol in SYMBOLS:
        try:
            res = build_analysis(symbol)
            print(res)
            send_telegram(res)
            time.sleep(4)  # Délai plus long
        except Exception as e:
            print(f"Erreur {symbol}: {e}")
