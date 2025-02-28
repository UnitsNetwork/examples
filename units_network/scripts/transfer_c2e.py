#!/usr/bin/env python
import sys

import pywaves as pw
from web3.types import Wei

from units_network import common_utils, networks, units
from units_network.args import Args
from units_network.cli_utils import find_asset


def main():
    log = common_utils.configure_cli_logger(__file__)

    args = Args()
    if not (args.waves_private_key and args.eth_private_key and args.amount > 0):
        print(
            """Transfer assets from Consensus Layer (Waves) to Execution Layer (Ethereum).
Usage:
  transfer-c2e.py --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet, W - MainNet 
  --asset-id <Waves asset id in Base58> (default: Unit0 of selected network)
  --asset-name <Waves asset name>: an alternative to --asset-id
  --amount N (default: 0.01): amount of transferred assets
  --args <path/to/args.json>: take default argument values from this file""",
            file=sys.stderr,
        )
        sys.exit(1)

    network = networks.create_manual(args.network_settings)

    cl_account = pw.Address(privateKey=args.waves_private_key)
    el_account = network.w3.eth.account.from_key(args.eth_private_key)

    asset = find_asset(network, args.asset_id, args.asset_name)  # noqa: F821
    log.info(
        f"[C] Selected asset '{asset.waves_asset_name}' with id {asset.waves_asset.assetId} and {asset.waves_asset.decimals} decimals"
    )

    cl_atomic_amount = units.user_to_atomic(args.amount, asset.waves_asset.decimals)
    el_atomic_amount = Wei(units.user_to_atomic(args.amount, asset.el_decimals))
    log.info(
        f"Sending {args.amount} assets from {cl_account.address} (C) to {el_account.address} (E)"
    )
    log.debug(f"C atomic units: {cl_atomic_amount}, E atomic units: {el_atomic_amount}")

    transfer_result = network.cl_chain_contract.transfer(
        cl_account, el_account.address, asset.waves_asset, cl_atomic_amount
    )

    log.info(f"[C] ChainContract.transfer result: {transfer_result}")
    log.info("Done")


if __name__ == "__main__":
    main()
