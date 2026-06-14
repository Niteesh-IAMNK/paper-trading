import uuid


def generate_id():
    return str(uuid.uuid4())


def round_price(price):
    return round(price, 2)