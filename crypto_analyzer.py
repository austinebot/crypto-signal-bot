import requests
import statistics
import os
import time
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def fetch_candles(symbol, interval="15m", limit=150):
    url = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        time.sleep(2)
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

def ema(values, period):
    if len(values) < period: return values
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out

def rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = statistics.mean(gains[-period:]) if gains else 0
    avg_loss = statistics.mean(losses[-period:]) if losses else 0
    if avg_loss == 0: return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)

def compute_adx(candles, period=14):
    if len(candles) < period + 1: return 20.0
    trs, plus_dm, minus_dm = [], [], []
    for i in range(1, len(candles)):
        c, p = candles[i], candles[i-1]
        tr = max(c['high']-c['low'], abs(c['high']-p['close']), abs(c['low']-p['close']))
        up = c['high'] - p['high']
        down = p['low'] - c['low']
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
        trs.append(tr)
    atr = statistics.mean(trs[-period:])
    plus_di = statistics.mean(plus_dm[-period:]) / atr * 100 if atr > 0 else 0
    minus_di = statistics.mean(minus_dm[-period:]) / atr * 100 if atr > 0 else 0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0
    return dx

def compute_macd(closes):
    if len(closes) < 35: return 0, 0
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd = [a - b for a, b in zip(ema12, ema26)]
    signal = ema(macd, 9)
    hist = [m - s for m, s in zip(macd, signal)]
    return hist[-1], hist[-2]

def find_s_r(candles):
    if not candles: return 0, 0
    price = candles[-1]['close']
    support = min(c['low'] for c in candles[-60:])
    resistance = max(c['high'] for c in candles[-60:])
    return support, resistance

def detect_pattern(candles):
    if len(candles) < 40: return "Pas de pattern clair"
    highs = [c['high'] for c in candles[-60:]]
    lows = [c['low'] for c in candles[-60:]]
    if max(highs[-30:]) > max(highs[:-30]) * 0.995 and max(highs[-15:]) > max(highs[:-15]) * 0.995:
        return "Double Top (baissier)"
    if min(lows[-30:]) < min(lows[:-30]) * 1.005 and min(lows[-15:]) < min(lows[:-15]) * 1.005:
        return "Double Bottom (haussier)"
    return "Pas de pattern clair"

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
            time.sleep(3)
        except Exception as e:
            print(f"Erreur {symbol}: {e}")
