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
https://hub.docker.com/r/vadimpy/solexample

First terminal (run localnet Solana blockchain):<br>
```bash
$ solana-test-validator -r
```

Second terminal (listen its logs):<br>
```bash
$ solana logs
```

Third terminal (deploy on-chain programs and run exmaples notebook):<br>
```bash
$ cd solanastocksim/stock_backend
$ ./deploy.sh
$ jupyter-notebook
```
Run example.ipynb cell-by-cell<br>
Be careful! Recommended system requirements for Solana's localnet are 24 logical CPUs and 64GB of memory

### Build
#### Build client:
```bash
$ cd solanastocksim/stock_frontend/rust_client
$ cargo +nightly build --target-dir ../build
```
#### Build on-chain programs:
```bash
$ cd solanastocksim/stock_backend
$ cargo +nightly build-bpf --bpf-out-dir build
```
Configure paths in `solanastocksim/cfg.yml` (for Docker it is already configured)

### Docker commands:
Run Jupyter notebook
```bash
sudo docker run --name vadimpy/solexample -it -p 8888:8888 -a stdin -a stdout -i -t vadimpy/solexample:latest /bin/bash
cd solanastocksim
jupyter notebook --ip 0.0.0.0 --allow-root
```



