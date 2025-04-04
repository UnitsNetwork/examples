# Unit0 examples

## Setup for development

- nix: `nix develop`
- other Linux and macOS: `./dev-setup.sh; source .venv/bin/activate`

## Glossary

- CL - Consensus Layer, Waves;
- EL - Execution Layer, Ethereum.

## Usage

Run any command without parameters to see the full list of options.

### Transfer from CL to EL

```bash
u0-transfer-c2e
```

### Transfer from EL to CL

```bash
u0-transfer-e2c
```

If you transfer a native token (Unit0), then you don't need to approve transfers for it.
Otherwise, run approve command before transferring assets.

#### Approve transfers from the Standard Bridge

You have to do this for registered asset transfers.

```bash
u0-erc20-approve
```

#### Prepare chain_contract.withdraw transaction from EL transfer transaction hash

In case if a transfer failed during the process.
You will need an EL transaction with a transfer from the logs and specify it in `--txn-hash` parameter.

```bash
u0-transfer-e2c-withdraw --txn-hash <Ethereum transaction hash in HEX>
```

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

CLI arguments has precedence over JSON arguments.

### Logging

You can configure the logging with a
custom [logging.conf](units_network/logging.conf) ([docs](https://docs.python.org/3/library/logging.config.html#logging-config-fileformat)).

The precedence (from higher to lower) of config files:
1. A path to the `logging.conf` file in the  `LOGGING_CONFIG` environment variable.
2. The `logging.conf` file in the current working directory.
3. The default `logging.conf` file in the `unit0-examples` package.
