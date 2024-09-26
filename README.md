# Unit0 examples

## Install

- nix: `nix develop`
- other Linux and macOS: `./setup.sh`
  If you want to develop, active the virtual environment: `source .venv/bin/activate`

## Usage

Run any command without parameters to see the full list of options.

### Transfer from EL to CL (Waves)

```bash
u0-transfer-e2c --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> 
```

#### Prepare chain_contract.withdraw transaction from EL transfer transaction hash

```bash
u0-transfer-e2c-withdraw.py --txn-hash <Ethereum transaction hash in HEX> --waves-private-key <Waves private key in base58> 
```

### Transfer from CL (Waves) to EL

```bash
u0-transfer-c2e.py --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

