class SafeAccountController:

    def notifier(self, ord_id):
        order = self.orders_tracker[ord_id]
        if order['type'] == 'sell':
            self.sell_orders_sum -= order['amount']
        else:
            self.buy_orders_sum -= order['price'] * order['amount']
        del self.orders_tracker[ord_id]
            

    def __init__(self, s):
        self.__stock = s
        acc_methods = s.create_random_acc(lambda ord_id : self.notifier(ord_id))

        self.id, \
        self.balance, \
        self.__buy_unsafe, \
        self.__sell_unsafe, \
        self.__place_buy_order_unsafe, \
        self.__place_sell_order_unsafe = acc_methods

        self.buy_orders_sum = 0
        self.sell_orders_sum = 0
        self.orders_tracker = dict()

    def place_sell_order(self, price, amount):
        _, vdoll = self.balance()
        if amount > vdoll - self.sell_orders_sum:
            return False

        ord_id = self.__place_sell_order_unsafe(price, amount)
        self.orders_tracker[ord_id] = {'type' : 'sell', 'price' : price, 'amount' : amount}
        self.sell_orders_sum += amount

        return True

    def place_buy_order(self, price, amount):
        doll, _ = self.balance()
        if price * amount > doll - self.buy_orders_sum:
            return False
        
        ord_id = self.__place_buy_order_unsafe(price, amount)
        self.orders_tracker[ord_id] = {'type' : 'buy', 'price' : price, 'amount' : amount}
        self.buy_orders_sum += price * amount

        return True

    def buy(self):
        doll, _ = self.balance()
        price, amount = self.__stock.sell_min_price_order
        if price == 0 and amount == 0:
            return False
        if price * amount > doll - self.buy_orders_sum:
            return False
        self.__buy_unsafe()
        return True

    def sell(self):
        _, vdoll = self.balance()
        price, amount = self.__stock.buy_max_price_order
        if price == 0 and amount == 0:
            return False
        if amount > vdoll - self.sell_orders_sum:
            return False
        self.__sell_unsafe()
        return True

    def close(self, ord_id):
        if ord_id not in self.orders_tracker:
            return False
        self.__stock.close(ord_id)
        return True

    def check_balance(self):
        doll, vdoll = self.balance()
        assert doll >= 0
        assert vdoll >= 0

    @property
    def buy_order(self):
        return self.__stock.sell_min_price_order
    
    @property
    def sell_order(self):
        return self.__stock.buy_max_price_order
    
    @property
    def last_price(self):
        return self.__stock.last_price

    @property
    def history(self):
        return self.__stock.history
