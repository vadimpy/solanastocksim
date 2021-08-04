from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.account import Account
from solana.transaction import Transaction, TransactionInstruction, AccountMeta
from solana.blockhash import Blockhash
from solana.system_program import create_account
from solana.system_program import CreateAccountParams
from solana.system_program import SYS_PROGRAM_ID

import yaml
import json
import os
import random
from time import sleep

PROGS_BUILD = "/home/vadimpy/Documents/algalon_test/stockback/build"
SENDER_KEY_PAIR  = f"{PROGS_BUILD}/sender-keypair.json"
LOGGER_KEY_PAIR  = f"{PROGS_BUILD}/logger-keypair.json"

def gen_private_key():
    return bytes([random.randint(0, 255) for _ in range(32)])

def get_keypair(path):
    with open(path, 'r') as f:
        res = json.load(f)
    return res[32:], res[:32] # pub, priv

def get_solana_config():
    cfg_path = os.path.join(os.path.expanduser('~'), '.config', 'solana', 'cli', 'config.yml')
    configYml = open(cfg_path, 'r')
    return yaml.safe_load(configYml)

class SolanaClient:

    def __init__(self, url=None):
        cfg = get_solana_config()
        if url is None:
            url = cfg['json_rpc_url']
        self.__identity = cfg['keypair_path']
        self.__c = Client(url)
        self.__min_bal = self.__c.get_minimum_balance_for_rent_exemption(0).get('result')
        self.__payer = Account()
        self.__c.request_airdrop(self.__payer.public_key(), 10000000000 + self.__min_bal)
        self.__wait_for_creation(self.__payer.public_key())
        sender_id, _ = get_keypair(SENDER_KEY_PAIR)
        self.__sender_id = PublicKey(sender_id)
        self.__default_space = 0

    def __wait_for_confirm(self, signature):
        k = 0
        status = self.__c.get_signature_statuses([signature])['result']['value'][0]
        while k < 30 and  status != 'confirmed':
            sleep(1)
            res = self.__c.get_signature_statuses([signature])['result']['value'][0]
            if res is not None:
                status = res['confirmationStatus']
            k += 1

        return status == 'confirmed'

    def __wait_for_creation(self, pub):
        k = 0
        res = self.__c.get_account_info(pub).get('result').get('value')
        while k < 30 and  res is None:
            k += 1
            sleep(1)
            res = self.__c.get_account_info(pub).get('result').get('value')

        return res is not None

    def create_account(self, priv_key, lamps):
        lamps += self.__min_bal
        acc = Account(priv_key)
        p = CreateAccountParams(self.__payer.public_key(), acc.public_key(), lamps, self.__default_space, self.__sender_id)
        insn = create_account(p)
        recent_blockhash = Blockhash(self.__c.get_recent_blockhash()['result']['value']['blockhash'])
        txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=self.__payer.public_key()).add(insn)
        self.__c.send_transaction(txn, self.__payer, acc)
        self.__wait_for_creation(acc.public_key())
        print("Acc created")
        return acc

    def get_balance(self, pub):
        return self.__c.get_balance(pub).get('result').get('value') - self.__min_bal
    
    @property
    def payer(self):
        return self.__payer

    def send_lamps(self, from_acc, to_acc, amount):

        insn_data = amount.to_bytes(8, 'little')
        
        from_acc_meta = AccountMeta(from_acc.public_key(), False, True)
        to_acc_meta   = AccountMeta(to_acc.public_key(), False, True)

        recent_blockhash = Blockhash(self.__c.get_recent_blockhash()['result']['value']['blockhash'])
        insn = TransactionInstruction([from_acc_meta, to_acc_meta], self.__sender_id, insn_data)
        txn = Transaction(recent_blockhash=recent_blockhash, fee_payer=self.__payer.public_key()).add(insn)

        self.__c.send_transaction(txn, self.__payer)
