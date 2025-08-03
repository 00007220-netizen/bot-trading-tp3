import time
import ccxt
import pandas as pd
from datetime import datetime
from twilio.rest import Client

# === CONFIGURACIÓN ===
API_KEY = 'uMoltteWJoRMFQfXxXSpuMyfAXAo38tgDwxf7Crf1z3rGkXkM0rfKX1sh0RYoQSP'
API_SECRET = 'ZDlKAwNdUfWSwKXksfe0e1igcNKbpY8ZoAufNolvIuMjHtonETkjRKCwGZrs8mEx'
TAKE_PROFIT_PCT = 3
MONEDAS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']
INTERVALO = 60  # segundos
ARCHIVO_OPERACIONES = 'operaciones.csv'

# Twilio WhatsApp (ya vinculado a +50371313364)
TWILIO_SID = 'TU_SID'
TWILIO_TOKEN = 'TU_TOKEN'
TWILIO_WHATSAPP_FROM = 'whatsapp:+14155238886'
WHATSAPP_TO = 'whatsapp:+50371313364'

# === INICIALIZACIÓN ===
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

client = Client(TWILIO_SID, TWILIO_TOKEN)

def enviar_alerta(mensaje):
    try:
        client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=WHATSAPP_TO,
            body=mensaje
        )
    except Exception as e:
        print(f"❌ Error enviando alerta: {e}")

def obtener_saldo_disponible():
    balance = exchange.fetch_balance()
    usdt = balance['total']['USDT']
    print(f"💰 Saldo disponible USDT: {usdt}")
    return usdt

def analizar_condiciones(moneda):
    ohlcv = exchange.fetch_ohlcv(moneda, timeframe='1m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Indicadores simples para ejemplo
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma50'] = df['close'].rolling(50).mean()
    
    if df['ma20'].iloc[-1] > df['ma50'].iloc[-1]:
        print(f"✅ Condición de compra detectada en {moneda}")
        return True
    return False

def ejecutar_operacion(moneda, usdt_disponible):
    ticker = exchange.fetch_ticker(moneda)
    precio = ticker['last']
    cantidad = round(usdt_disponible / precio, 6)

    orden = exchange.create_market_buy_order(moneda, cantidad)
    print(f"📈 Comprado {moneda} a {precio} (Cantidad: {cantidad})")

    operacion = {
        'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        'symbol': moneda,
        'precio_compra': precio,
        'cantidad': cantidad,
        'order_id': orden['id']
    }

    guardar_operacion(operacion)
    enviar_alerta(f"📈 Comprado {moneda} a {precio:.2f} USDT")

def guardar_operacion(op):
    df = pd.DataFrame([op])
    try:
        df.to_csv(ARCHIVO_OPERACIONES, mode='a', header=not pd.io.common.file_exists(ARCHIVO_OPERACIONES), index=False)
    except Exception as e:
        print(f"❌ Error guardando operación: {e}")

def revisar_take_profit(exchange, operacion, moneda, take_profit_pct):
    try:
        symbol = operacion['symbol']
        order_id = operacion['order_id']
        cantidad = float(operacion['cantidad'])
        precio_compra = float(operacion['precio_compra'])

        order_info = exchange.fetch_order(order_id, symbol)
        if order_info['status'] == 'closed':
            print(f"🚪 Operación en {symbol} ya fue cerrada anteriormente.")
            return None

        ticker = exchange.fetch_ticker(symbol)
        precio_actual = ticker['last']
        ganancia_pct = ((precio_actual - precio_compra) / precio_compra) * 100

        print(f"📊 {symbol} | Precio Compra: {precio_compra:.4f} | Actual: {precio_actual:.4f} | Ganancia: {ganancia_pct:.2f}%")

        if ganancia_pct >= take_profit_pct:
            orden_venta = exchange.create_market_sell_order(symbol, cantidad)
            print(f"✅ ¡Take Profit alcanzado en {symbol}! Vendido a {precio_actual:.4f}")
            enviar_alerta(f"✅ ¡TP alcanzado! Vendido {symbol} a {precio_actual:.2f}")
            return {
                'symbol': symbol,
                'orden': orden_venta,
                'ganancia_pct': ganancia_pct
            }

    except Exception as e:
        print(f"❌ Error al revisar Take Profit para {moneda}: {e}")
    return None

def main():
    print("🚀 BOT DE TRADING INICIADO 🚀")
    while True:
        try:
            operaciones = []
            if pd.io.common.file_exists(ARCHIVO_OPERACIONES):
                operaciones = pd.read_csv(ARCHIVO_OPERACIONES).to_dict(orient='records')

            monedas_ya_operadas = [op['symbol'] for op in operaciones]

            if not monedas_ya_operadas:
                saldo = obtener_saldo_disponible()
                for moneda in MONEDAS:
                    if analizar_condiciones(moneda):
                        ejecutar_operacion(moneda, saldo)
                        break  # Solo una moneda por ciclo

            else:
                for op in operaciones:
                    revisar_take_profit(exchange, op, op['symbol'], TAKE_PROFIT_PCT)

        except Exception as e:
            print(f"❌ Error en bucle principal: {e}")

        print(f"⌛ Esperando {INTERVALO} segundos...\n")
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()
