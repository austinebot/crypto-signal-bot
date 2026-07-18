import requests
import statistics
import os
import time
from datetime import datetime

def fetch_candles(symbol, interval="15m", limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
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

# Le reste du code reste identique (ema, rsi, etc.)

def build_analysis(symbol):
    time.sleep(1)  # Délai important pour éviter le rate limit
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

# === Le reste du code (functions ema, rsi, etc. + main) reste identique ===

# Copie le reste du code de ma précédente réponse (les fonctions ema, rsi, compute_adx, etc. + la partie CONFIG et send_telegram)

# ... (colle ici le reste du code que je t'ai donné avant)

if __name__ == "__main__":
    for symbol in SYMBOLS:
        try:
            res = build_analysis(symbol)
            print(res)
            send_telegram(res)
            time.sleep(2)  # Délai entre chaque symbole
        except Exception as e:
            print(f"Erreur {symbol}: {e}")
