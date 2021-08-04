from faststock import Stock
from safeacc import SafeAccountController as Account
import random
from strats import SimpleStrat

def main():
    s = Stock('stock.log')
    accs_amount = 5
    accounts = [Account(s) for _ in range(accs_amount)]
    bots = [SimpleStrat(acc, 50 + random.randint(-10, 10)) for acc in accounts]
    for i in range(200):
        for bot in bots:
            bot.make_decision()
            bot.acc.check_balance()
        s.dump_accounts_table()
        s.dump_order_book()
        random.shuffle(bots)
    s.dump_history()

if __name__ == "__main__":
    main()
