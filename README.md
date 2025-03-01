# Unit0 examples

## Setup for development

- nix: `nix develop`
- other Linux and macOS: `./dev-setup.sh; source .venv/bin/activate`

## Usage

Run any command without parameters to see the full list of options.

### Allow transfers from a standard bridge

You have to do this for registered asset transfers.
```bash
u0-erc20-approve --eth-private-key <Ethereum private key in HEX with 0x> --asset-id <Waves asset id in Base58> 
```

### Transfer from EL to CL (Waves)

```bash
u0-transfer-e2c --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> | jq .
```

#### Prepare chain_contract.withdraw transaction from EL transfer transaction hash

```bash
u0-transfer-e2c-withdraw --txn-hash <Ethereum transaction hash in HEX> --waves-private-key <Waves private key in base58> 
```

### Transfer from CL (Waves) to EL

```bash
u0-transfer-c2e --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

### Logging

You can configure logging with a custom [logging.conf](./units_network/scripts/logging.conf) ([docs](https://docs.python.org/3/library/logging.config.html#logging-config-fileformat)). Then you need to specify a
path to this file in the `LOGGING_CONFIG` environment variable.

### Convenient way to provide arguments for commands

Instead of providing arguments, you can write a JSON file and load arguments from it using `--args path/to/args.json`. 

Here is an example for consensus client
[local-network](https://github.com/UnitsNetwork/consensus-client/tree/main/local-network):
```json
{
  "waves_private_key": "DwPvPGEp3LPg5gVRz7Pqd8mHa6dWK9dXtP4XDmKTz6ga",
  "eth_private_key": "0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63",
  "network_settings": {
    "name": "LocalNet",
    "cl_chain_id_str": "D",
    "cl_node_api_url": "http://127.0.0.1:16869",
    "el_node_api_url": "http://127.0.0.1:18545",
    "chain_contract_address": "3FXDd4LoxxqVLfMk8M25f8CQvfCtGMyiXV1"
  },
  "asset_name": "TestToken"
}
```
