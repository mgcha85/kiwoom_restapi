
def get_tick_price(price):
    """
    주식의 가격에 따라 호가 단위를 계산합니다.
    :param price: 주식의 현재 가격
    :return: 호가 단위
    """
    if price < 2000:
        return 1
    elif price < 5000:
        return 5
    elif price < 20000:
        return 10
    elif price < 50000:
        return 50
    elif price < 200000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000


def calculate_tick_price(price):
    tick_price = get_tick_price(price)
    return int((price // tick_price) * tick_price)