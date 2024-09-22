#!/usr/bin/env .venv/bin/python
import os
import sys
from typing import List

import pywaves as pw
from eth_account.signers.base import BaseAccount
from web3 import Web3
from web3.types import FilterParams, Nonce, TxParams, Wei

import common_utils
from merkle import get_merkle_proofs
from networks import select_network

log = common_utils.configure_script_logger(os.path.basename(__file__))

cl_account_private_key = common_utils.get_argument_value("--waves-private-key")
el_account_private_key = common_utils.get_argument_value("--eth-private-key")
chain_id_str = common_utils.get_argument_value("--chain-id") or "S"
raw_amount = common_utils.get_argument_value("--amount") or "0.01"

if not (cl_account_private_key and el_account_private_key):
    print(
        """Transfer native tokens from Execution Layer (Ethereum) to Consensus Layer (Waves).
At least two arguments required:
  ./transfer-e2c.ts --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> 
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet. Not supported for now: W - MainNet
  --amount N (default: 0.01): amount of transferred Unit0 tokens""",
        file=sys.stderr,
    )
    exit(1)

network = select_network(chain_id_str)

cl_account = pw.Address(privateKey=cl_account_private_key)
el_account = network.w3.eth.account.from_key(el_account_private_key)

amount = Web3.to_wei(raw_amount, "ether")
log.info(
    f"Sending {raw_amount} Unit0 ({amount} Wei) from {el_account.address} (E) to {cl_account.address} (C) using Bridge on {network.el_bridge_contract.address} (E)"
)


# Send a request from EL to CL
def send_native(
    from_eth_account: BaseAccount,
    to_waves_account: pw.Address,
    amount: Wei,
    gas_price: Wei,
    nonce: Nonce = Nonce(0),
):
    cl_account_pk_hash_bytes = common_utils.waves_public_key_hash_bytes(
        to_waves_account.address
    )
    txn: TxParams = {
        "from": from_eth_account.address,
        "nonce": nonce,
        "gasPrice": gas_price,
        "value": amount,
    }
    send_native_call = network.el_bridge_contract.functions.sendNative(
        cl_account_pk_hash_bytes
    )
    gas = send_native_call.estimate_gas(txn)
    txn.update(
        {
            "to": network.el_bridge_contract.address,
            "gas": gas,
            "data": send_native_call._encode_transaction_data(),
        }
    )
    signed_tx = network.w3.eth.account.sign_transaction(txn, el_account_private_key)
    log.debug(f"[E] Signed sendNative transaction: {Web3.to_json(signed_tx)}")
    return network.w3.eth.send_raw_transaction(signed_tx.raw_transaction)


log.info("[E] Call Bridge sendNative")
current_gas_price_wei = network.w3.eth.gas_price
send_native_result = send_native(
    el_account,
    cl_account,
    amount,
    network.w3.eth.gas_price,
    nonce=network.w3.eth.get_transaction_count(el_account.address),
)

send_native_receipt = network.w3.eth.wait_for_transaction_receipt(send_native_result)
log.info(f"[E] sendNative receipt: {Web3.to_json(send_native_receipt)}")

block_hash_with_transfer = send_native_receipt.blockHash.hex()
block_logs = network.w3.eth.get_logs(
    FilterParams(
        blockHash=block_hash_with_transfer,
        address=network.el_bridge_contract.address,
        topics=[network.el_send_native_topic],
    )
)
log.info(
    f"[E] Bridge logs in block 0x{block_hash_with_transfer} by topic '0x{network.el_send_native_topic}': {Web3.to_json(block_logs)}"
)

merkle_leaves = []
transfer_index_in_block = -1
for i, x in enumerate(block_logs):
    merkle_leaves.append(x["data"].hex())
    if x.transactionHash == send_native_receipt.transactionHash:
        transfer_index_in_block = i

log.info(
    f"[E] Transfer index: {transfer_index_in_block}, Merkle tree leaves in block: {merkle_leaves}"
)

merkle_proofs = get_merkle_proofs(merkle_leaves, transfer_index_in_block)
log.info(f"[C] Merkle tree proofs for withdraw: {merkle_proofs}")

# Wait for a block confirmation on Consensus layer
withdraw_block_meta = network.cl_chain_contract.waitForBlock(block_hash_with_transfer)
log.info(f"[C] Withdraw block meta: {withdraw_block_meta}, wait for finalization")
network.cl_chain_contract.waitForFinalized(withdraw_block_meta)


def withdraw(
    sender: pw.Address,
    block_hash_with_transfer: str,
    merkle_proofs: List[str],
    transfer_index_in_block: int,
    amount: Wei,
):
    proofs = [
        {"type": "binary", "value": f"base64:{common_utils.hex_to_base64(p)}"}
        for p in merkle_proofs
    ]
    withdraw_amount = amount // (10**10)
    log.info(f"[C] Withdraw amount: {withdraw_amount}")
    params = [
        {"type": "string", "value": block_hash_with_transfer},
        {"type": "list", "value": proofs},
        {"type": "integer", "value": transfer_index_in_block},
        {"type": "integer", "value": withdraw_amount},
    ]
    return sender.invokeScript(
        dappAddress=network.cl_chain_contract.oracleAddress,
        functionName="withdraw",
        params=params,
        txFee=500_000,
    )


withdraw_result = withdraw(
    cl_account, block_hash_with_transfer, merkle_proofs, transfer_index_in_block, amount
)
log.info(f"[C] Withdraw result: {withdraw_result}")
log.info("Done")
