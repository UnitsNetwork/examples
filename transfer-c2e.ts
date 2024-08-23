import { BigNumber } from "@waves/bignumber";
import * as waves from '@waves/node-api-js';
import * as wavesTransactions from '@waves/waves-transactions';
import { Web3 } from 'web3';
import * as commonUtils from './common-utils';
import { getNetwork } from "./networks";
import { C2ETransfer } from "./types";

const chainIdStr = commonUtils.getArgumentValue('--chain-id') || 'S'; // StageNet by default
const chainId = chainIdStr.charCodeAt(0);

const amount = commonUtils.getArgumentValue('--amount') || '0.01';

const clAccountPrivateKey = commonUtils.getArgumentValue('--waves-private-key');
const elAccountPrivateKey = commonUtils.getArgumentValue('--eth-private-key');
if (!(clAccountPrivateKey && elAccountPrivateKey)) {
  console.error(
    'Transfer native tokens from Consensus Layer (Waves) to Execution Layer.\n\
At least two arguments required:\n\
  npx tsx transfer-cl-to-el.ts --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>\n\
Additional optional arguments:\n\
  --chain-id <S|T|W>, S by default: S - StageNet, not suported for now: T - TestNet, W - MainNet\n\
  --amount N, 0.01 by default: amount of transferred Unit0 tokens'
  );
  process.exit(1);
}

const network = getNetwork(chainIdStr);
console.log(`Network: ${network.name}`);

const clAccountPublicKey = wavesTransactions.libs.crypto.publicKey({ privateKey: clAccountPrivateKey });
const clAccountAddress = wavesTransactions.libs.crypto.address({ publicKey: clAccountPublicKey }, chainId);

let wavesApi = waves.create(network.clNodeApiUrl);

let ecApi = new Web3(network.elNodeApiUrl);
ecApi.eth.transactionConfirmationBlocks = 1;
ecApi.eth.transactionBlockTimeout = 10;
ecApi.eth.transactionPollingTimeout = 120000;
ecApi.eth.transactionPollingInterval = 3000;
ecApi.eth.defaultAccount = elAccountPrivateKey;

const elAccount = ecApi.eth.accounts.privateKeyToAccount(elAccountPrivateKey);

const transfer: C2ETransfer = {
  elRecipientAddress: elAccount.address,
  amount: new BigNumber(amount).mul(new BigNumber(10).pow(8)).toString() // amount * 10^8
};

const tokenId = (await wavesApi.addresses.fetchDataKey(network.chainContractAddress, 'tokenId')).value;
if (!commonUtils.isString(tokenId)) throw new Error(`Expected tokenId to be a string, got: ${tokenId}`);
console.log(`Token id: ${tokenId}`);

function signC2ERequest(clSenderPrivateKey: string, chainContractAddress: string, transfer: C2ETransfer, assetIdB58: String): any {
  return wavesTransactions.invokeScript(
    {
      dApp: chainContractAddress,
      call: {
        function: "transfer",
        args: [
          { type: 'string', value: transfer.elRecipientAddress.slice(2) }, // Without 0x
        ]
      },
      payment: [
        {
          amount: transfer.amount,
          assetId: assetIdB58
        }
      ],
      fee: 500000,
      chainId: chainIdStr
    },
    {
      privateKey: clSenderPrivateKey
    }
  );
}

console.log(`Sending ${amount} Unit0 from ${clAccountAddress} in Consensus (Waves) Layer to ${elAccount.address} in Execution Layer`);
const transferSignedTx = signC2ERequest(clAccountPrivateKey, network.chainContractAddress, transfer, tokenId);

// Sending the transfer transaction to CL

const transferSignedTxResult = await wavesApi.transactions.broadcast(transferSignedTx);
console.log('CL->EL transfer result:');
console.dir(transferSignedTxResult, { depth: null });
