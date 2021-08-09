use stocksim_client as sol_cli;
use solana_sdk::signer::keypair;
use std::convert::TryInto;

fn main() {

    unsafe {
        let c = sol_cli::SolanaClient::new();

        let ac1 = keypair::Keypair::new().to_bytes();
        let ac2 = keypair::Keypair::new().to_bytes();

        let pub1 : [u8; 32] = ac1[32..].try_into().unwrap();
        let pub2 : [u8; 32] = ac2[32..].try_into().unwrap();

        c.create_account(&ac1, 193);
        c.create_account(&ac2, 278);

        c.send_lamports(&pub1, &pub2, 14);
        let b1 = c.get_balance(&pub1);
        let b2 = c.get_balance(&pub2);

        println!("{} {}", b1, b2);
    }
}