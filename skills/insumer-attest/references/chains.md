# Chain Coverage

InsumerAPI evaluates wallet conditions on **37 chains** total: 31 EVM, plus Solana, XRPL, Bitcoin, Tron, Stellar, and Sui.

## EVM (31 chains)

Pass `chainId` as the canonical numeric ID. Merkle storage proofs (`proof: "merkle"`) are available on **27 of 31 EVM chains**. The four without are ZKsync Era (324), Sei (1329), Viction (88) and XDC Network (50). No non-EVM chain has them.

Full supported set, from the canonical `ChainId` enum in <https://insumermodel.com/openapi.yaml>:

| Chain | chainId |
|---|---|
| Ethereum | 1 |
| OP Mainnet (Optimism) | 10 |
| BNB Smart Chain | 56 |
| Viction | 88 |
| Gnosis | 100 |
| Unichain | 130 |
| Polygon | 137 |
| Sonic | 146 |
| opBNB | 204 |
| zkSync Era | 324 |
| Scroll | 534352 |
| World Chain | 480 |
| Mantle | 5000 |
| Linea | 59144 |
| Blast | 81457 |
| Base | 8453 |
| Soneium | 1868 |
| Ronin | 2020 |
| Berachain | 80094 |
| Sei | 1329 |
| ApeChain | 33139 |
| Celo | 42220 |
| Arbitrum One | 42161 |
| Avalanche C-Chain | 43114 |
| Ink | 57073 |
| Plume | 98866 |
| Chiliz | 88888 |
| Taiko | 167000 |
| XDC Network | 50 |
| Robinhood Chain | 4663 |
| Arc | 5042 |

For the always-current canonical list, check the `ChainId` schema in <https://insumermodel.com/openapi.yaml>.

## Non-EVM (6 chains)

For these chains, use the dedicated wallet field (not `wallet`) and pass the chainId as a string:

| Chain | chainId | Wallet field | Native unit | Token type field | Merkle proof |
|---|---|---|---|---|---|
| Solana | `"solana"` | `solanaWallet` | SOL (9 decimals) | SPL token by mint address (`contractAddress`) | ✗ |
| XRPL | `"xrpl"` | `xrplWallet` | XRP (`contractAddress: "native"`) | Trust line tokens (`currency` field) | ✗ |
| Bitcoin | `"bitcoin"` | `bitcoinWallet` | BTC (`contractAddress: "native"`) | n/a | ✗ |
| Tron | `"tron"` | `tronWallet` | TRX (`contractAddress: "native"`) | TRC-20 by contract address | ✗ |
| Stellar | `"stellar"` | `stellarWallet` | XLM (`contractAddress: "native"`) | Classic trustline assets (issuer G-address + `assetCode`) | ✗ |
| Sui | `"sui"` | `suiWallet` | SUI (`contractAddress: "0x2::sui::SUI"`; `"native"` is a `400` on Sui) | Any other coin by its full coin type (`address::module::Name`) | ✗ |

### XRPL specifics

- XRP balance: `contractAddress: "native"`
- Trust line tokens (RLUSD, USDC on XRPL): `contractAddress` is the issuer r-address, plus `currency` field (e.g. `"RLUSD"`, `"USDC"`, or any 3-char code). Currency codes are case-sensitive: send the code exactly as the issuer created it (`USD` and `usd` are different currencies). `XRP` is the native coin and is not accepted as a currency: use `contractAddress: "native"`
- 3-char currency codes pass through as-is; longer names (e.g. `"RLUSD"`) are auto hex-encoded to the 40-char XRPL canonical format
- NFTokens use `taxon` field for issuer + taxon filtering

### Bitcoin specifics

- Only native BTC balance is supported (no Ordinals, no BRC-20)
- Address types accepted: P2PKH, P2SH, bech32 (P2WPKH/P2WSH), Taproot (P2TR)
- BTC balance threshold is in **BTC** (not satoshis) — the API handles satoshi conversion internally

### Solana specifics

- Native SOL balance: `contractAddress: "native"`
- SPL token balance: `contractAddress` is the mint address (base58)
- USDC on Solana mint: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- USDT on Solana mint: `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`

## Decimals

`decimals` is optional. Leave it out: the token's own decimals are always read from the chain. If sent it is only a cross-check, and a value that differs from the token's own decimals is rejected with a `400` naming the token's value. Native coins are fixed (18 on EVM chains, 6 for TRX, 9 for SUI).

The `threshold` is always in display units, as a decimal string: `"100"` means 100 USDC whatever the token's decimals are. Do not guess a token's decimals from its symbol. The same stablecoin can have different decimals on different chains.

## See also

- [InsumerAPI OpenAPI spec — `ChainId` enum](https://insumermodel.com/openapi.yaml)
- [Developer docs — verification](https://insumermodel.com/developers/verification/)
