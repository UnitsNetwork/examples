#!/usr/bin/env python
import sys

import pywaves as pw
from web3 import Web3
from web3.types import TxReceipt, Wei

from units_network import common_utils, networks, units
from units_network.args import Args


def main():
    log = common_utils.configure_cli_logger(__file__)

    args = Args()
    if not (args.eth_private_key and args.asset_id and args.amount > 0):
        print(
            """Approves token movements from Execution Layer (Ethereum) to Consensus Layer (Waves).
Usage:
  erc20_approve.py --eth-private-key <Ethereum private key in HEX with 0x> --asset-id <Waves asset id in Base58>
Required arguments:
  --asset-id <Waves asset id in Base58>: the matching ERC20 address will be found in the chain contract registry
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet. W - MainNet
  --amount N (default: 0.01): amount of transferred Unit0 tokens
  --args <path/to/args.json>: take default argument values from this file""",
            file=sys.stderr,
        )
        exit(1)

    network = networks.create_manual(args.network_settings)
    asset = pw.Asset(args.asset_id)
    registered_asset = network.cl_chain_contract.getRegisteredAssetSettings(asset)
    if not registered_asset:
        raise Exception(f"{args.asset_id} is not a registered in the chain contract")

    erc20 = network.get_erc20(registered_asset.el_erc20_address)
    el_atomic_amount = Wei(units.user_to_atomic(args.amount, erc20.decimals))
    log.info(
        f"Approving a transfer of {args.amount} (in atomic units: {el_atomic_amount}) assets '{erc20.name}' at {registered_asset.el_erc20_address}"
    )

    el_account = network.w3.eth.account.from_key(args.eth_private_key)
    approve_txn_hash = erc20.approve(
        network.bridges.standard_bridge.contract_address, el_atomic_amount, el_account
    )
    approve_receipt: TxReceipt = network.w3.eth.wait_for_transaction_receipt(
        approve_txn_hash,
    )
    log.info(f"ERC20.approve receipt: {Web3.to_json(approve_receipt)}")  # type: ignore
    log.info("Done")


if __name__ == "__main__":
    main()
