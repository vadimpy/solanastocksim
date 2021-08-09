#!/usr/bin/bash
programs=("sender" "setter" "messenger")
for prog in "${programs[@]}"; do
    echo "Deploying ${prog}"
    echo "command: solana program deploy build/${prog}.so"
    solana program deploy "build/${prog}.so";
done