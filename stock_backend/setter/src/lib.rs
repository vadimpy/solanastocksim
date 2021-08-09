use borsh::BorshDeserialize;
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    pubkey::Pubkey,
    // log::sol_log_params
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

    msg!("Setter is called!");
    let account_info_iter = &mut accounts.iter();    
    let account_info = next_account_info(account_info_iter)?;

    if !account_info.is_signer {
        msg!("Account is not signer!");
        return Ok(())
    }

    if !account_info.is_writable {
        msg!("Account is not writable!");
        return Ok(())
    }

    let ref mut acc_data = **account_info.data.borrow_mut();

    let insn_len = instruction_data.len();
    let acc_data_len = acc_data.len();

    let min_len =  if insn_len < acc_data_len { insn_len } else { acc_data_len };

    acc_data[..min_len].clone_from_slice(&instruction_data[..min_len]);
    msg!("Data was successfully copied");

    Ok(())
}
