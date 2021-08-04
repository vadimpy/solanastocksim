use borsh::BorshDeserialize;
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    pubkey::Pubkey,
    log::sol_log_params
};

#[derive(BorshDeserialize, Debug)]
pub struct AmountHodler {
    pub amount: u64,
}

entrypoint!(process_instruction);
pub fn process_instruction(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {

    sol_log_params(accounts, instruction_data);

    let account_info_iter = &mut accounts.iter();
    

    let source_info = next_account_info(account_info_iter)?;
    let destination_info = next_account_info(account_info_iter)?;

    let holder = AmountHodler::try_from_slice(&instruction_data)?;
    let amount = holder.amount;

    **source_info.try_borrow_mut_lamports()? -= amount;
    **destination_info.try_borrow_mut_lamports()? += amount;

    msg!("Transaction:");
    msg!("\tfrom: ");
    msg!("\tto: ");
    msg!("\tamount: {}", amount);

    Ok(())
}
