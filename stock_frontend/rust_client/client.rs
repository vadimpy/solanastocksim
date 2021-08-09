// Solana developers provide three crates to work with their technology
// SolanaSDK - a set of datastructures
// Solana Client - Rust API for blockchain to create and send transactions
// Solana Program - crate for creating on-chain programs and custom tokens       

use {
    solana_sdk::{
        account::Account,
        pubkey::Pubkey,
        signer::{keypair, Signer},
        transaction::Transaction,
    },
    solana_client::rpc_client::RpcClient,
    solana_program::{
        system_instruction::create_account,
        instruction::Instruction,
        instruction::AccountMeta,
        system_program::id as system_program_id
    },
    serde_yaml,
    serde_derive::Deserialize,
    std::collections::HashMap,
    std::fmt::Debug,
    // serde_json,
    rand,
    std::fs::File,
    pyo3::prelude::*,
    pyo3::types::PyBytes,
};

#[derive(Deserialize, Debug)]
struct ClientCfg {
    solana_cfg_path: Option<String>,
    client_type: Option<String>,
    programs: Option<HashMap<String, String>>,
}

// Parse config file for client. This file contains solana-test-validator config path
// and paths to deployed programs' keypairs

fn get_client_cfg(path: &str) -> ClientCfg {
    let file = File::open(path).unwrap();
    serde_yaml::from_reader(file).unwrap()
}

// When solana-test-validator starts, it crates config file, that contains address for JSON RPC communication and other stuff

fn get_solana_config(path: &str) -> serde_yaml::Value {
    let file = File::open(path).unwrap();
    serde_yaml::from_reader(file).unwrap()
}

// 'solana program deploy' cli command deploys on-chain program on localnet, every program has a public key, by default it is created
// by cargo while building on-chain program and stored near of .so file 

fn get_keypair(path: &str) -> [u8; 64] {
    keypair::read_keypair_file(path).unwrap().to_bytes()
}

// Rust-only wrapper

struct SolanaClientImpl {
    client : RpcClient,
    min_bal : u64,
    default_space : usize, // default memory space of an account (Solana's account is like a file, it can store data between invokations of on-chain programs)
                           // default_space stands for initial availiable memory size for each account
    payer_pub: Pubkey, // TODO: support acc struct that will hold pub and private
    payer_keypair: keypair::Keypair, // a keypair of a rich account that pays commisions
    sender_id : Pubkey, // public key of on-chain program that sends lamports between accounts
    messenger_id : Pubkey, // on-chain program that sends user's message to localnet's log
    setter_id : Pubkey, // on-chain program to set account's data 
}

impl SolanaClientImpl {

    fn new(cfg_path: &str) -> SolanaClientImpl {

        // parse input cfg file

        let ClientCfg {solana_cfg_path, client_type, programs} = get_client_cfg(cfg_path);
        let solana_cfg_path = solana_cfg_path.unwrap();
        // let client_type = client_type.unwrap(); // unused for now, but can be used to connect to devnet
        let programs = programs.unwrap();

        // get RPC JSON address:port and create a client

        let sol_cfg = get_solana_config(&solana_cfg_path);
        let url = String::from(sol_cfg["json_rpc_url"].as_str().unwrap());
        let client = solana_client::rpc_client::RpcClient::new(url);

        // get minimum lamports balance of an account without any memory
        // it is unable to create an account without lamports an a localnet

        let default_space : usize = 0;
        let min_bal = client.get_minimum_balance_for_rent_exemption(default_space).unwrap();

        // create a rich payer thatt stands for commisions paying

        let payer_bal = 100000000000 + min_bal;
        let payer_keypair = keypair::Keypair::new();
        let payer_pub = Pubkey::new(&payer_keypair.to_bytes()[32..]);

        // Airdrop is a localnet, testnet and devnet only rest-api request, processing which Solana's blockchain nodes create an account with
        // particular lamports (lamports is a minimal part of Solana's native token SOL) 

        let signature = client.request_airdrop(&payer_pub, payer_bal).unwrap(); // send request
        client.poll_for_signature(&signature); // wait for confirmation by polling transaction status

        // get_balance is Rest API request to get balance of particular pubkey

        let tmp = client.get_balance(&payer_pub).unwrap();
        println!("\n{}\n", tmp);

        // get keypairs of on-chain programs

        let sender_keypair = get_keypair(&programs["sender"]);
        let sender_id = Pubkey::new(&sender_keypair[32..]);

        let messenger_keypair = get_keypair(&programs["messenger"]);
        let messenger_id = Pubkey::new(&messenger_keypair[32..]);

        let setter_keypair = get_keypair(&programs["setter"]);
        let setter_id = Pubkey::new(&setter_keypair[32..]);


        // return a client wrapper

        SolanaClientImpl {client, min_bal, default_space, payer_keypair, payer_pub, sender_id, messenger_id, setter_id,}
    }

    fn create_account(&self, keypair: &keypair::Keypair, lamps: u64) {

        // Obviously this function stands for creating accounts which is strange when
        // being introduced to airdrop request.
        // Airdrop request calls so called System Program - preloaded on-chain program
        // that is the main way to create an account. Processing airdrop requenst, some node
        // calls system program with an argument "owner" equals to system program public key.
        // Only owners can withdraw lamports from an accounts, so we need to create accounts
        // owned by our own sender on-chain program

        // Calculate corrected balance and create a public key wrapper from public key scratch
        
        let lamps = lamps + self.min_bal;
        let new_acc_pub = Pubkey::new(&keypair.to_bytes()[32..]);

        // Get a hash of the latest block in blockchain which will be inserted into transaction

        let (hash, _) = self.client.get_recent_blockhash().unwrap();
 
        // Create an instruction with a helper from Solana Program package
        // Instruction is bytes vector, which on-chain program is free to interpret however
        // Helper creates an instruction to invoke account creator in System Program
        // Further, this instruction is added to a transaction, this transaction must be
        // signed by a fee payer private key and new account private key 

        let insn = create_account(&self.payer_pub, &new_acc_pub, lamps, self.default_space as u64, &self.sender_id); // create account, withdraw its lamports from payer
        let signers = [&self.payer_keypair, &keypair]; // specify signers - accounts, that sign a transaction scratch with their private keys
        let txn = Transaction::new_signed_with_payer(&[insn], Some(&self.payer_pub), &signers, hash); // create transaction

        // Simulate transaction, send it and poll for status until transaction is confirmed
        // Simulation is needed for example, that sum balances of accounts related to particular
        // transaction stays the same after all on-chain programs invokations as before 
        let res = self.client.send_and_confirm_transaction(&txn).unwrap();

        let bal = self.client.get_balance(&new_acc_pub).unwrap();
        println!("{}", bal);
    }

    fn create_account_with_space(&self, keypair: &keypair::Keypair, space: usize) {

        // Solana accounts have a memory which can be used to pass a state between instructions processing
        // This memory simply is a byte array
        // This method creates an account with minimal balance and particular space (in bytes) with use of system program

        let lamps = self.min_bal;
        let new_acc_pub = Pubkey::new(&keypair.to_bytes()[32..]);
        let (hash, _) = self.client.get_recent_blockhash().unwrap();

        // create account owned by setter on chain program to let it changes account's data
        let insn = create_account(&self.payer_pub, &new_acc_pub, lamps, space as u64, &self.setter_id);
        let signers = [&self.payer_keypair, &keypair];
        let txn = Transaction::new_signed_with_payer(&[insn], Some(&self.payer_pub), &signers, hash);
        let res = self.client.send_and_confirm_transaction(&txn).unwrap();
    }

    fn set_account_data(&self, keypair: &keypair::Keypair, data: &[u8]) {

        // This method sets account data with use of our setter on-chain program

        let acc_pub = Pubkey::new(&keypair.to_bytes()[32..]);
        let acc_meta = AccountMeta::new(acc_pub, true); // create writable signer account meta
        let (hash, _) = self.client.get_recent_blockhash().unwrap();

        let insn = Instruction::new_with_bytes(self.setter_id, data, vec![acc_meta]);
        let signers = [&self.payer_keypair, &keypair];
        let txn = Transaction::new_signed_with_payer(&[insn], Some(&self.payer_pub), &signers, hash);

        let res = self.client.send_and_confirm_transaction(&txn).unwrap();
    }

    fn get_account_data(&self, pub_key: &Pubkey) -> Vec<u8> {
        // get accounts data with Solana API's corresponding request
        self.client.get_account_data(pub_key).unwrap()
    }   

    fn send_lamports(&self, from_pub: &Pubkey, to_pub: &Pubkey, amount: u64) {

        // This method calls our own sender on-chain program
        // To call particular on-chain program, we have to specify any accounts
        // that can be available for a program, program's pubkey and a fee payer

        // On-chain program gets structure called AccountMeta for each account. Account meta includes
        // account's public key and two flags: is this account signer of a transaction and is this account's memory writable

        let from_meta = AccountMeta::new(*from_pub, false); // "new" builder by default creates writable account
        let to_meta   = AccountMeta::new(*to_pub, false);   // false stands for "isn't signer"
        let (hash, _) = self.client.get_recent_blockhash().unwrap();

        // BORSH (acronim) is binary serializer/deserializer, provides convinient and efficient interface
        // to serialize/deserialize structures from/to byte vectors
        let insn = Instruction::new_with_borsh(self.sender_id, &amount, vec![from_meta, to_meta]);
        let signers = [&self.payer_keypair];
        let txn = Transaction::new_signed_with_payer(&[insn], Some(&self.payer_pub), &signers, hash);

        // Code of sender can be found in backend.

        let res = self.client.send_and_confirm_transaction(&txn).unwrap();
    }

    // method to get corrected balance
    fn get_balance(&self, pub_key: &Pubkey) -> u64 {
        self.client.get_balance(pub_key).unwrap() - self.min_bal
    }

    // Method sends specified message to localnet's log

    fn send_message_to_logs(&self, mes: &str) {
        let (hash, _) = self.client.get_recent_blockhash().unwrap();
        let insn = Instruction::new_with_borsh(self.messenger_id, &String::from(mes), vec![]);
        let signers = [&self.payer_keypair];
        let txn = Transaction::new_signed_with_payer(&[insn], Some(&self.payer_pub), &signers, hash);
        let res = self.client.send_and_confirm_transaction(&txn).unwrap();
    }   
}
// pyo3 macros to create Python-native shared object which will provide access to rust-only functions

#[pymodule]
pub fn rust_client(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SolanaClient>()?;
    m.add_function(wrap_pyfunction!(gen_keypair, m)?)?;
    Ok(())
}

// though documentation says, rust Vec<u8> transforms to Python bytes,
// it is actually transformed to Python list, so result of calling this function from python
// should be wrapped with bytes(..)

#[pyfunction]
fn gen_keypair() -> Vec<u8> {
    keypair::Keypair::new().to_bytes().to_vec()
}


#[pyclass]
struct SolanaClient {
    client: SolanaClientImpl,
}

#[pymethods]
impl SolanaClient {
    #[new]
    fn new(cfg_path: &str) -> PyResult<Self> {
        Ok(Self { client: SolanaClientImpl::new(cfg_path) })
    }

    pub fn create_account(&self, keypair: &[u8], lamps: u64) -> PyResult<bool> {
        let keypair = keypair::Keypair::from_bytes(keypair).unwrap();
        self.client.create_account(&keypair, lamps);
        Ok(true)
    }

    pub fn create_account_with_space(&self, keypair: &[u8], space: usize) -> PyResult<bool> {
        let keypair = keypair::Keypair::from_bytes(keypair).unwrap();
        self.client.create_account_with_space(&keypair, space);
        Ok(true)
    }

    pub fn set_account_data(&self, keypair: &[u8], data: &[u8]) -> PyResult<bool> {
        let keypair = keypair::Keypair::from_bytes(keypair).unwrap();
        self.client.set_account_data(&keypair, data);
        Ok(true)
    }

    pub fn get_account_data(&self, pub_key: &[u8]) -> PyResult<Vec<u8>> {
        let pub_key = Pubkey::new(pub_key);
        Ok(self.client.get_account_data(&pub_key))
    }

    pub fn send_lamports(&self, from_pub: &[u8], to_pub: &[u8], lamps: u64) -> PyResult<bool> {
        let from_pub = Pubkey::new(from_pub);
        let to_pub = Pubkey::new(to_pub);
        self.client.send_lamports(&from_pub, &to_pub, lamps);
        Ok(true)
    }

    pub fn get_balance(&self, pub_key: &[u8]) -> u64 {
        let pub_key = Pubkey::new(pub_key);
        self.client.get_balance(&pub_key)
    }

    pub fn send_message_to_logs(&self, mes: &str) -> PyResult<bool> {
        self.client.send_message_to_logs(mes);
        Ok(true)
    }
}

// Raw C interface
// For future to create C/C++/Cython bindings with cbindgen

/*#[repr(C)]
pub struct SolanaClient {
    client_impl: SolanaClientImpl
}

impl SolanaClient {
    #[no_mangle]
    pub unsafe extern "C" fn new() -> SolanaClient {
        SolanaClient { client_impl: SolanaClientImpl::new() }
    }
    #[no_mangle]
    pub unsafe extern "C" fn create_account(&self, keypair: &[u8; 64], lamps: u64) -> bool {
        let keypair = keypair::Keypair::from_bytes(keypair).unwrap();
        self.client_impl.create_account(&keypair, lamps);
        true
    }
    #[no_mangle]
    pub unsafe extern "C" fn send_lamports(&self, from_pub: &[u8; 32], to_pub: &[u8; 32], lamps: u64) -> bool {
        let from_pub = Pubkey::new(from_pub);
        let to_pub = Pubkey::new(to_pub);
        self.client_impl.send_lamports(&from_pub, &to_pub, lamps);
        true
    }
    #[no_mangle]
    pub unsafe extern "C" fn get_balance(&self, pub_key: &[u8; 32]) -> u64 {
        let pub_key = Pubkey::new(pub_key);
        self.client_impl.get_balance(&pub_key)
    }
}*/
