#!/usr/bin/env python
import json
import sys

import pywaves as pw
from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import Web3
from web3.types import TxReceipt

from units_network import common_utils, networks, units
from units_network.args import Args
from units_network.native_bridge import SentNative
from units_network.standard_bridge import ERC20BridgeInitiatedEvent


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
    txn_receipt: TxReceipt = network.w3.eth.get_transaction_receipt(txn_hash)
    log.info(f"[E] Bridge.sendNative transaction receipt: {Web3.to_json(txn_receipt)}")  # type: ignore
    assert "blockHash" in txn_receipt

    transfer_evt = next(
        (
            network.bridges.parse_e2c_event(x)
            for x in txn_receipt["logs"]
            if x["address"] == network.bridges.native_bridge.contract_address
            or x["address"] == network.bridges.standard_bridge.contract_address
        ),
        None,
    )

    if isinstance(transfer_evt, SentNative):
        asset = network.cl_chain_contract.getNativeToken()
        cl_amount = transfer_evt.amount
        pass
    elif isinstance(transfer_evt, ERC20BridgeInitiatedEvent):
        asset = network.cl_chain_contract.getRegisteredAssetByErc20(
            transfer_evt.local_token
        )
        if not asset:
            raise Exception(
                f"Can't find a registered asset by ERC20 address: {transfer_evt.local_token}"
            )
        cl_amount = transfer_evt.cl_amount
        pass
    else:
        raise Exception("Can't find a transfer log in receipt")

    log.info(
        f"Found event: {transfer_evt}. Amount: {units.atomic_to_user(cl_amount, asset.decimals)}, asset: {asset.name.decode("ascii")}"
    )

    transfer_params = network.bridges.get_e2c_transfer_params(
        txn_receipt["blockHash"], txn_hash
    )
    log.info(f"[C] Transfer params: {transfer_params}")

    withdraw = network.cl_chain_contract.prepareWithdrawAsset(
        cl_account,
        transfer_params.block_with_transfer_hash,
        transfer_params.merkle_proofs,
        transfer_params.transfer_index_in_block,
        cl_amount,
        asset,
    )
    print(json.dumps(withdraw))
    log.info("Done")


if __name__ == "__main__":
    main()
