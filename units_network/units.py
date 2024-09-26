from web3 import Web3
from web3.types import Wei


def raw_to_wei_amount(raw_amount: float) -> Wei:
    return Web3.to_wei(raw_amount, "ether")


def raw_to_waves_atomic_amount(raw_amount: float) -> int:
    # Issued token has 8 decimals, we need to calculate amount in atomic units https://docs.waves.tech/en/blockchain/token/#atomic-unit
    return int(raw_amount * 10**8)
