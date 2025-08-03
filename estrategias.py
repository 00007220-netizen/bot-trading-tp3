def obtener_senal_compra(exchange, par, timeframe):
    try:
        velas = exchange.fetch_ohlcv(par, timeframe, limit=100)
        if not velas or len(velas) < 50:
            return False

        cierres = [vela[4] for vela in velas]

        # RSI
        def calcular_rsi(data, period=14):
            subidas, bajadas = [], []
            for i in range(1, len(data)):
                cambio = data[i] - data[i - 1]
                subidas.append(max(cambio, 0))
                bajadas.append(abs(min(cambio, 0)))
            avg_subida = sum(subidas[-period:]) / period
            avg_bajada = sum(bajadas[-period:]) / period
            rs = avg_subida / avg_bajada if avg_bajada != 0 else 0
            return 100 - (100 / (1 + rs))

        rsi = calcular_rsi(cierres)

        # MACD
        def calcular_ema(data, periodo):
            k = 2 / (periodo + 1)
            ema = data[0]
            for precio in data[1:]:
                ema = precio * k + ema * (1 - k)
            return ema

        ema12 = calcular_ema(cierres[-26:], 12)
        ema26 = calcular_ema(cierres[-26:], 26)
        macd = ema12 - ema26

        # Bandas de Bollinger
        def calcular_bollinger(data, period=20):
            if len(data) < period:
                return None, None, None
            sma = sum(data[-period:]) / period
            std = (sum((x - sma) ** 2 for x in data[-period:]) / period) ** 0.5
            return sma + 2 * std, sma, sma - 2 * std

        upper, middle, lower = calcular_bollinger(cierres)

        return rsi < 30 and macd > 0 and cierres[-1] < lower

    except Exception as e:
        print(f"Error en señal de compra para {par}: {e}")
        return False
