from hexbytes import HexBytes


class TimeExhausted(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class BlockNotFound(Exception):
    def __init__(self, block_hash: HexBytes):
        super().__init__(f"Block {block_hash.to_0x_hex()} not found on contract")


class BlockDisappeared(Exception):
    def __init__(self, block_hash: HexBytes):
        super().__init__(
            f"Block {block_hash.to_0x_hex()} disappeared from execution client"
        )
