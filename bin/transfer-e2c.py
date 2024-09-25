#!/usr/bin/env .venv/bin/python
import os
import sys

import pywaves as pw
from web3 import Web3
from web3.types import TxReceipt

from units_network import common_utils
from units_network.networks import Network


def main():
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

    network = Network.select(chain_id_str)

    cl_account = pw.Address(privateKey=cl_account_private_key)
    el_account = network.w3.eth.account.from_key(el_account_private_key)

    amount = Web3.to_wei(raw_amount, "ether")
    log.info(
        f"Sending {raw_amount} Unit0 ({amount} Wei) from {el_account.address} (E) to {cl_account.address} (C) using Bridge on {network.el_bridge.address} (E)"
    )

    log.info("[E] Call Bridge sendNative")
    send_native_result = network.el_bridge.sendNative(
        from_eth_account=el_account,
        to_waves_pk_hash=common_utils.waves_public_key_hash_bytes(cl_account.address),
        amount=amount,
    )

    send_native_receipt: TxReceipt = network.w3.eth.wait_for_transaction_receipt(
        send_native_result
    )
    log.info(f"[E] sendNative receipt: {Web3.to_json(send_native_receipt)}")  # type: ignore

    transfer_params = network.el_bridge.getTransferParams(
        send_native_receipt["blockHash"], send_native_receipt["transactionHash"]
    )
    log.info(f"[C] Transfer params: {transfer_params}")

    # Wait for a block confirmation on Consensus layer
    withdraw_block_meta = network.cl_chain_contract.waitForBlock(
        transfer_params.block_with_transfer_hash.hex()
    )
    log.info(f"[C] Withdraw block meta: {withdraw_block_meta}, wait for finalization")
    network.cl_chain_contract.waitForFinalized(withdraw_block_meta)

    withdraw_result = network.cl_chain_contract.withdraw(
        cl_account,
        transfer_params.block_with_transfer_hash.hex(),
        transfer_params.merkle_proofs,
        transfer_params.transfer_index_in_block,
        amount,
    )
    log.info(f"[C] Withdraw result: {withdraw_result}")
    log.info("Done")


if __name__ == "__main__":
    main()
