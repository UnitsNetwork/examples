# Unit0 examples

## Install

```bash
npm i
```

## Usage

### Transfer from EL to CL (Waves)

```bash
npx tsx transfer-e2c.ts --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

See more options:
```bash
npx tsx transfer-e2c.ts
```

### Transfer from CL (Waves) to EL

```bash
npx tsx transfer-c2e.ts --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>
```

See more options:
```bash
npx tsx transfer-c2e.ts
```
