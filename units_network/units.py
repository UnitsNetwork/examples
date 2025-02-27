from decimal import Decimal

UNIT0_EL_DECIMALS = 18


def user_to_atomic(amount: Decimal, asset_decimals: int) -> int:
    return int(amount.scaleb(asset_decimals))


def atomic_to_user(amount: int, asset_decimals: int) -> Decimal:
    return Decimal(amount).scaleb(-asset_decimals)
