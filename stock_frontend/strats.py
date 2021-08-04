import random
from statistics import mean

class StratBase:
    def __init__(self, acc):
        random.seed()
        self.acc = acc
    def make_decision(self):
        raise NotImplementedError

class SimpleStrat(StratBase):
    def __init__(self, acc, threshold):
        self.__th = threshold
        self.__orders_time_tracker = {}
        super().__init__(acc)

    def __get_available_doll(self):
        doll, _ = self.acc.balance()
        return doll - self.acc.buy_orders_sum

    def __get_available_vdoll(self):
        _, vdoll = self.acc.balance()
        return vdoll - self.acc.sell_orders_sum

    def __track_old_orders(self):
        to_delete = []
        for order_id in self.acc.orders_tracker.keys():
            if order_id not in self.__orders_time_tracker:
                self.__orders_time_tracker[order_id] = 1
            elif self.__orders_time_tracker[order_id] == 20:
                to_delete.append(order_id)
            else:
                self.__orders_time_tracker[order_id] += 1
        for order_id in to_delete:
            self.acc.close(order_id)
        if len(to_delete) > 10:
            self.__estimate_trend()

    def __estimate_trend(self):
        his_len = len(self.acc.history)
        tail_size = 20
        if his_len >= tail_size:
            self.__th = (self.__th + int(mean(self.acc.history[his_len - tail_size:]))) // 2 + 2

    def make_decision(self):
        self.__track_old_orders()
        sell_price, sell_amount = self.acc.sell_order
        buy_price, buy_amount = self.acc.buy_order

        vdoll_available = self.__get_available_vdoll()
        doll_available = self.__get_available_doll()

        if vdoll_available != 0:
            sell_amount = random.randint(1, vdoll_available // 2 + vdoll_available % 2)

        if sell_price == 0 and sell_amount == 0:
            if vdoll_available != 0:
                self.acc.place_sell_order(self.__th + 1, sell_amount)
        elif sell_price >= self.__th:
            res = self.acc.sell()
            if not res:
                if vdoll_available != 0:
                    price = random.randint(self.__th, 2 * sell_price - self.__th)
                    self.acc.place_sell_order(price, sell_amount)

        if buy_price == 0 and buy_amount == 0:
            available_amount = doll_available // (self.__th - 1)
            if available_amount != 0: 
                self.acc.place_buy_order(self.__th - 1, random.randint(1, available_amount // 2 + available_amount % 2))
        elif buy_price < self.__th:
            res = self.acc.buy()
            if not res:
                available_amount = doll_available // buy_price
                if available_amount != 0: 
                    price = random.randint(2 * buy_price - self.__th, self.__th)
                    self.acc.place_buy_order(buy_price, random.randint(1, available_amount // 2 + available_amount % 2))

    @property
    def threshold(self):
        return self.__th

    def set_threshold(self, th):
        self.__th = th

# TODO: wrap to class for tests
def rand_strat(acc):
    actions = ['sell', 'buy', 'place_sell', 'place_buy', 'close', 'hold']
    action = random.choice(actions)

    if action == 'sell':
        acc.sell()
    elif action == 'buy':
        acc.buy()
    elif action == 'place_sell':
        price = random.randint(1, 10)
        amount = random.randint(1, 10)
        acc.place_sell_order(price, amount)
    elif action == 'place_buy':
        price = random.randint(1, 10)
        amount = random.randint(1, 10)
        acc.place_buy_order(price, amount)
    elif action == 'close':
        if len(acc.orders_tracker.keys()) != 0:
            order_id = random.choice(list(acc.orders_tracker.keys()))
            acc.close(order_id)
