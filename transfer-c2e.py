#!/usr/bin/env .venv/bin/python
import sys

import pywaves as pw
from eth_account.signers.base import BaseAccount
from web3 import Web3

import common_utils
from chain_contract import ChainContract
from networks import get_network

log = common_utils.configure_script_logger("transfer-c2e")

cl_account_private_key = common_utils.get_argument_value("--waves-private-key")
el_account_private_key = common_utils.get_argument_value("--eth-private-key")
chain_id_str = common_utils.get_argument_value("--chain-id") or "S"
user_amount = common_utils.get_argument_value("--amount") or "0.01"

if not (cl_account_private_key and el_account_private_key):
    print(
        """Transfer native tokens from Consensus Layer (Waves) to Execution Layer (Ethereum).
At least two arguments required:
  ./transfer-cl-to-el.py --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
Additional optional arguments:
  --chain-id <S|T|W> (default: S): S - StageNet, T - TestNet, Not supported for now: W - MainNet 
  --amount N (default: 0.01): amount of transferred Unit0 tokens""",
        file=sys.stderr,
    )
    sys.exit(1)

network = get_network(chain_id_str)
log.info(f"Network: {network.name}")

pw.setNode(network.cl_node_api_url, network.chain_id_str)
chain_contract = ChainContract(oracleAddress=network.chain_contract_address)
cl_account = pw.Address(privateKey=cl_account_private_key)

w3 = Web3(Web3.HTTPProvider(network.el_node_api_url))
el_account = w3.eth.account.from_key(el_account_private_key)

# Issued token has 8 decimals, we need to calculate amount in atomic units https://docs.waves.tech/en/blockchain/token/#atomic-unit
atomic_amount = int(float(user_amount) * 10**8)

log.info(
    f"Sending {user_amount} Unit0 ({atomic_amount} in atomic units) from {cl_account.address} (C) to {el_account.address} (E)"
)

token = chain_contract.getToken()
log.info(f"[C] Token id: {token.assetId}")


# Sign the transfer request
def transfer(
    from_waves_account: pw.Address,
    to_eth_account: BaseAccount,
    token: pw.Asset,
    atomic_amount: int,
):
    return from_waves_account.invokeScript(
        dappAddress=chain_contract.oracleAddress,
        functionName="transfer",
        params=[
            {
                "type": "string",
                "value": to_eth_account.address.lower()[2:],  # Remove '0x' prefix
            }
        ],
        payments=[{"amount": atomic_amount, "assetId": token.assetId}],
        txFee=500_000,
    )


transfer_result = transfer(cl_account, el_account, token, atomic_amount)
log.info(f"[C] Transfer result: {transfer_result}")
log.info("Done")
