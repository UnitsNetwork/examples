# Unit0 examples

## Install

- nix: `nix develop`
- other Linux and macOS: `./setup.sh`
  If you want to develop, active the virtual environment: `source .venv/bin/activate`

## Usage

### Transfer from EL to CL (Waves)

```bash
./transfer-e2c.py --eth-private-key <Ethereum private key in HEX with 0x> --waves-private-key <Waves private key in base58> 
```

See more options:
```bash
./transfer-e2c.py
```

### Transfer from CL (Waves) to EL

```bash
npx tsx transfer-c2e.ts --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

See more options:
```bash
npx tsx transfer-c2e.ts
```
