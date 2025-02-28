#!/usr/bin/env python
import json
import sys

import pywaves as pw
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxData

from units_network import common_utils, networks
from units_network.args import Args


def main():
    log = common_utils.configure_cli_logger(__file__)

    args = Args()
    if not (args.waves_private_key and args.txn_hash):
        print(
            """Prepares the chain_contract.withdraw transaction from an Execution Layer (Ethereum) transaction hash.
Usage:
  transfer-e2c-withdraw.py --txn-hash <Ethereum transaction hash in HEX> --waves-private-key <Waves private key in base58> 
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet. W - MainNet
  --args <path/to/args.json>: take default argument values from this file""",
            file=sys.stderr,
        )
        exit(1)

    network = networks.create_manual(args.network_settings)
    cl_account = pw.Address(privateKey=args.waves_private_key)

    txn_hash = HexBytes(Web3.to_bytes(hexstr=HexStr(args.txn_hash)))
    txn_data: TxData = network.w3.eth.get_transaction(txn_hash)
    assert "blockHash" in txn_data and "value" in txn_data

    log.info(f"[E] Bridge.sendNative transaction data: {Web3.to_json(txn_data)}")  # type: ignore

    transfer_params = network.bridges.get_e2c_transfer_params(
        txn_data["blockHash"], txn_hash
    )
    log.info(f"[C] Transfer params: {transfer_params}")

    withdraw = network.cl_chain_contract.prepareWithdraw(
        cl_account,
        transfer_params.block_with_transfer_hash,
        transfer_params.merkle_proofs,
        transfer_params.transfer_index_in_block,
        txn_data["value"],
    )
    print(json.dumps(withdraw))
    log.info("Done")


if __name__ == "__main__":
    main()
