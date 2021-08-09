# solanastocksim
## Fun stock simulator integrated with Solana blockchain

### Structure
Whole thing consists from several parts:
 - _faststock.py, strats.py, safeacc.py_ - parts of stock exchange model. They stand for trade simulation
 - _rust_client_ - wrapper of Solana's RPC client & Python interface for stock model to track transactions on Solana's blockchain
 - _client.py_ - Python RPC client wrapper with SolanaPy python package, just a python implementation of rust_client (it was created to study API)
 - _sender, setter, messenger_ - on-chain programs, that are to be deployed on a localnet Solana's blockchain

### Run
Ready-to-use docker image:<br>

First terminal (run localnet Solana blockchain):<br>
`$ cd solanastocksim`<br>
`$ solana-test-validator -r`<br>

Second terminal (listen its logs):<br>
`$ cd solanastocksim`<br>
`$ solana logs`<br>

Third terminal (deploy on-chain programs and run exmaples notebook):<br>
`$ cd solanastocksim/stock_backend`<br>
`$ ./deploy.sh`<br>
`$ source ~/venv/bin/activate`<br>
`$ jupyter-notebook`<br>
Run example.ipynb cell-by-cell<br>
Be careful! Recommended system requirements for Solana's localnet are 24 logical CPUs and 64GB of memory

### Build
#### Build client:
`$ cd solanastocksim/stock_frontend/rust_client`<br>
`$ cargo +nightly build --target-dir ../build`<br>
#### Build on-chain programs:
`$ cd solanastocksim/stock_backend`<br>
`$ cargo build-bpf --bpf-out-dir build`<br>


Configure paths in `solanastocksim/cfg.yml`

