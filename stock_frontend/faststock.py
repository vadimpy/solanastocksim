import heapq
import random
from stock_frontend.rust_client import SolanaClient, gen_keypair
# from client import SolanaClient, gen_private_key

class Stock:

    class __Order:
        def __init__(self, price, meta):
            self.price = price
            self.meta = meta
    
    class __Sell_Order(__Order):
        def __le__(self, other):
            return self.price <= other.price
        def __lt__(self, other):
            return self.price < other.price

    class __Buy_Order(__Order):
        def __le__(self, other):
            return self.price >= other.price
        def __lt__(self, other):
            return self.price > other.price

    class __AccountData:
        def __init__(self, doll, vdoll, notifier):
            self.doll = doll
            self.vdoll = vdoll
            self.notifier = notifier

    __next_acc_id = 0
    __doll_cap = 0
    __vdoll_cap = 0
    __next_order_id = 0

    def __init__(self, client_cfg, log_fname=None):
        random.seed()
        self.__solana = SolanaClient(client_cfg)
        self.__sell_orders = []
        self.__buy_orders  = []
        self.__log = None
        if log_fname is not None:
            self.__log = open(log_fname, 'w')
        self.__accs_table = dict()
        self.__history = []

        self.__id2sol_acc = dict()

        self.__dump("Stock log:\n")

    def __del__(self):
        if self.__log is not None:
            self.__log.close()
    
    def __dump(self, *args, **kwargs):
        if self.__log is not None:
            self.__log.write(*args, **kwargs)

    @property
    def sell_min_price_order(self):
        if len(self.__sell_orders) == 0:
            return 0, 0
        return self.__sell_orders[0].price, self.__sell_orders[0].meta['amount']

    @property
    def buy_max_price_order(self):
        if len(self.__buy_orders) == 0:
            return 0, 0
        return self.__buy_orders[0].price, self.__buy_orders[0].meta['amount']

    def __place_buy_order(self, id_, price, amount):
        order_meta = {'acc_id' : id_, 'ord_id' : self.__next_order_id, 'amount' : amount}
        order = self.__Buy_Order(price, order_meta)
        heapq.heappush(self.__buy_orders, order)

        self.__dump(f"\nBuy order:\n\tid: {id_}\n\tamount: {amount}\n\tprice: {price}\n")

        self.__next_order_id += 1

        return self.__next_order_id - 1
    
    def __place_sell_order(self, id_, price, amount):
        order_meta = {"acc_id" : id_, "ord_id" : self.__next_order_id, "amount" : amount}
        order = self.__Sell_Order(price, order_meta)
        heapq.heappush(self.__sell_orders, order)

        self.__dump(f"\nSell order:\n\tid: {id_}\n\tamount: {amount}\n\tprice: {price}\n")

        self.__next_order_id += 1

        return self.__next_order_id - 1
    
    def __buy(self, buyer_id):
        order = heapq.heappop(self.__sell_orders)
        price = order.price
        meta = order.meta
        seller_id = meta['acc_id']
        order_id = meta['ord_id']
        amount = meta['amount']

        self.__accs_table[buyer_id].doll -= price * amount
        self.__accs_table[buyer_id].vdoll += amount

        self.__accs_table[seller_id].doll += price * amount
        self.__accs_table[seller_id].vdoll -= amount

        from_acc = self.__id2sol_acc[seller_id][32:] # extract public key from keypair
        to_acc   = self.__id2sol_acc[buyer_id][32:]
        self.__solana.send_lamports(from_acc, to_acc, amount)

        self.__accs_table[seller_id].notifier(order_id)

        self.__history.append(price)
        self.__dump(f"\nSell transaction:\n\torder id: {order_id}\n\tbuyer id: {buyer_id}\n\tseller id: {seller_id}\n\tprice: {price}\n\tamount: {amount}\n")

    def __sell(self, seller_id):
        order = heapq.heappop(self.__buy_orders)
        price = order.price
        meta = order.meta
        buyer_id = meta['acc_id']
        order_id = meta['ord_id']
        amount = meta['amount']

        self.__accs_table[buyer_id].doll -= price * amount
        self.__accs_table[buyer_id].vdoll += amount

        self.__accs_table[seller_id].doll += price * amount
        self.__accs_table[seller_id].vdoll -= amount

        from_acc = self.__id2sol_acc[seller_id][32:]
        to_acc   = self.__id2sol_acc[buyer_id][32:]
        self.__solana.send_lamports(from_acc, to_acc, amount)

        self.__accs_table[buyer_id].notifier(order_id)

        self.__history.append(price)
        self.__dump(f"\nBuy transaction:\n\torder id: {order_id}\n\tbuyer id: {buyer_id}\n\tseller id: {seller_id}\n\tprice: {price}\n\tamount: {amount}\n")

    def __extract_order(self, orders, i):
        acc_id = orders[i].meta['acc_id']
        ord_id = orders[i].meta['ord_id']
        self.__accs_table[acc_id].notifier(ord_id)
        del orders[i]
        heapq.heapify(orders)
        self.__dump(f"\nOrder {ord_id} was closed\n")

    def close(self, ord_id): 
        for i in range(len(self.__sell_orders)):
            if self.__sell_orders[i].meta['ord_id'] == ord_id:
                self.__extract_order(self.__sell_orders, i)
                return
        for i in range(len(self.__buy_orders)):
            if self.__buy_orders[i].meta['ord_id'] == ord_id:
                self.__extract_order(self.__buy_orders, i)
                return

    def create_random_acc(self, notifier):
        id_ = self.__next_acc_id
        doll = random.randint(100000, 200000)
        vdoll = random.randint(100000, 200000)

        self.__doll_cap += doll
        self.__vdoll_cap += vdoll

        self.__accs_table[id_] = self.__AccountData(doll, vdoll, notifier)

        sell_method = lambda : self.__sell(id_)
        buy_method = lambda : self.__buy(id_)
        balance_method = lambda : (self.__accs_table[id_].doll, self.__accs_table[id_].vdoll)
        place_sell_method = lambda price, amount : self.__place_sell_order(id_, price, amount)
        place_buy_method = lambda price, amount : self.__place_buy_order(id_, price, amount)

        self.__dump(f"\nNew account:\n\tid: {id_}\n\tdoll: {doll}\n\tvdoll: {vdoll}\n")

        self.__next_acc_id += 1

        solana_acc = bytes(gen_keypair()) # pyo3 rust crate should return bytes, but accidently it returns list
        self.__solana.create_account(solana_acc, vdoll)
        self.__id2sol_acc[id_] = solana_acc

        return (id_, balance_method, buy_method, sell_method, place_buy_method, place_sell_method)

    def dump_accounts_table(self):
        self.__dump("\nAccounts table:\n")
        for acc_id, acc_data in self.__accs_table.items():
            self.__dump(f"\tid: {acc_id}; doll: {acc_data.doll}; vdoll: {acc_data.vdoll}\n")

    def dump_order_book(self):
        self.__dump("\nOrder book:\n")

        self.__dump("\tSell:\n")
        for order in sorted(self.__sell_orders, key = lambda x : x.price):
            price = order.price
            meta = order.meta
            self.__dump(f"\t\torder id: {meta['ord_id']}; acc id: {meta['acc_id']}; price: {price}; amount: {meta['amount']}\n")
        
        self.__dump("\tBuy:\n")
        for order in sorted(self.__buy_orders, key = lambda x : x.price):
            price = order.price
            meta = order.meta
            self.__dump(f"\t\torder id: {meta['ord_id']}; acc id: {meta['acc_id']}; price: {price}; amount: {meta['amount']}\n")

    @property
    def history(self):
        return self.__history

    @property
    def last_price(self):
        return self.__history[-1]

    def dump_history(self):
        self.__dump(f"\nPrice history: {self.history}\n")

    def dump_solana_balances(self):
        self.__dump(f"\nSolana balances:\n")
        for id_, acc in self.__id2sol_acc.items():
            pub_key = acc[32:]
            balance = self.__solana.get_balance(pub_key)
            self.__dump(f"\t{id_} : {balance}\n")
