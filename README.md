# Unit0 examples

## Setup for development

- nix: `nix develop`
- other Linux and macOS: `./dev-setup.sh; source .venv/bin/activate`

## Usage

Run any command without parameters to see the full list of options.

### Transfer from EL to CL (Waves)

```bash
u0-transfer-e2c --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> | jq .
```

#### Prepare chain_contract.withdraw transaction from EL transfer transaction hash

```bash
u0-transfer-e2c-withdraw.py --txn-hash <Ethereum transaction hash in HEX> --waves-private-key <Waves private key in base58> 
```

### Transfer from CL (Waves) to EL

```bash
u0-transfer-c2e.py --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

### Logging

You can configure logging with a custom [logging.conf](./units_network/scripts/logging.conf) ([docs](https://docs.python.org/3/library/logging.config.html#logging-config-fileformat)). Then you need to specify a
path to this file in the `LOGGING_CONFIG` environment variable.
