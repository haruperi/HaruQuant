from technicals import *



def random(symbol):
    """
    Generates a random buy or sell signal.

    Args:
        symbol: The symbol (string) for which the signal is being generated.

    str: A string indicating the generated signal: "<symbol> Buy", "<symbol> Sell", or "<symbol> Neutral".
    """
    values = [-1, 0, 1]
    signal = np.random.choice(values)

    if signal == 1:
        return f"{symbol} Buy"
    elif signal == -1:
        return f"{symbol} Sell"
    else:
        return f"{symbol} Neutral"