FreeSwapP2P Wallet “Database” — README
This app doesn’t use a traditional SQL/NoSQL server. Your “database” is the wallet state on disk, made of two parts:

Stronghold snapshot (vault.stronghold) — an encrypted keystore that contains your seed/mnemonic and secrets.

Wallet storage (RocksDB) (rocksdb_storage/) — a local key–value database the IOTA SDK uses to cache accounts, addresses, outputs, and transaction metadata for fast sync.

Together, these files are your wallet’s persistent state.

Where it lives
Each wallet is stored under your Documents folder, grouped by Account Name (the first parameter you pass in):

Windows

pgsql
Copy
Edit
C:\Users\<You>\Documents\Stronghold\<AccountName>\
│
├─ vault.stronghold          # encrypted keystore (Stronghold)
└─ rocksdb_storage\          # local RocksDB database (SDK cache/index)
Cross-platform (conceptual)

perl
Copy
Edit
~/Documents/Stronghold/<AccountName>/
    vault.stronghold
    rocksdb_storage/
AccountName is whatever you pass as NameYourAcount to CreateWallet, RecoverWallet, or SignInToAccount.

The account alias inside the wallet is the second parameter (in your code you use the PIN/username string for this). The alias is used when selecting an account within a wallet.

What each file/dir does
vault.stronghold
Encrypted store for your mnemonic/seed and private keys. It’s protected with STRONGHOLD_PASSWORD. Without this file and the correct password, you cannot spend from the wallet (unless you still have the original mnemonic).

rocksdb_storage/
Local cache: account indexes, addresses, outputs, tx metadata. It speeds up syncing. If lost, it can usually be re-created by syncing (as long as you still have vault.stronghold + password or mnemonic to recover).

Environment variables
The module reads:

bash
Copy
Edit
# .env (loaded by python-dotenv) or process env
NODE_URL=https://api.shimmer.network
STRONGHOLD_PASSWORD=<your stronghold password>
NODE_URL picks which node/network to use (e.g., Shimmer mainnet).

STRONGHOLD_PASSWORD is required to open the Stronghold snapshot.

You can keep these in a local .env next to your Python file(s).

Lifecycle overview
Create
CreateWallet(AccountName, PinOrAlias, Password)
Generates a new mnemonic, writes vault.stronghold, creates rocksdb_storage/, creates an account with alias = PinOrAlias, and returns the mnemonic string. Back it up immediately.

Recover
RecoverWallet(AccountName, PinOrAlias, Password, mnemonic)
Creates a new Stronghold from the provided mnemonic. Fails if vault.stronghold already exists at that path.

Sign in
SignInToAccount(AccountName, PinOrAlias, Password)
Opens the Stronghold and loads the wallet. Returns (wallet, accountsInfo).

Backing up safely (Recommended)
Back up both the Stronghold file and the RocksDB folder. The Stronghold file is critical; RocksDB is rebuildable but backing it up shortens re-sync time.

PowerShell example:

powershell
Copy
Edit
$base = "$env:USERPROFILE\Documents\Stronghold\<AccountName>"
$dest = "D:\Backups\FreeSwapP2P\<AccountName>_$(Get-Date -Format yyyyMMdd_HHmmss)"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item "$base\vault.stronghold" $dest
Copy-Item "$base\rocksdb_storage" $dest -Recurse
Also keep a separate copy of your mnemonic offline (paper, password manager, hardware vault). The mnemonic alone can recover funds on any machine.

Restoring / Migrating to another machine
Install dependencies and the app.

Copy your backup to the new machine at:

php-template
Copy
Edit
<User>\Documents\Stronghold\<AccountName>\
    vault.stronghold
    rocksdb_storage\
Ensure STRONGHOLD_PASSWORD matches the original.

Call SignInToAccount(AccountName, PinOrAlias, Password).

If you only have the mnemonic, call RecoverWallet(...) to recreate vault.stronghold.

Resetting or deleting
If you want a fresh wallet under the same AccountName, delete or move that account’s folder first:

php-template
Copy
Edit
C:\Users\<You>\Documents\Stronghold\<AccountName>\
Deleting this folder without a copy of your mnemonic (or without knowing STRONGHOLD_PASSWORD) will permanently lock you out of the funds in that wallet.

Security notes
Protect vault.stronghold and STRONGHOLD_PASSWORD. Anyone with both can spend your funds.

Never commit vault.stronghold, rocksdb_storage/, or your mnemonic to Git/GitHub.

Consider disk encryption and offline/air-gapped backups for your seed.

Mnemonic shown by Create Account in the UI is for one time display; copy and store it securely.

Troubleshooting
“Invalid password” or cannot open wallet:
Check STRONGHOLD_PASSWORD. It must match what was used to create the Stronghold file.

Sync is slow or stuck:
Try sync_account(wallet, alias). As a last resort, stop the app and rename rocksdb_storage/ — it will rebuild on next sync (you’ll just wait longer).

Wrong network balances:
Verify NODE_URL points to the intended network (mainnet vs testnet). Using the wrong node makes balances look “missing”.

Session vs. database:
API sessions (bearer tokens) are in-memory on the server and not part of this on-disk database. Logging out only clears server memory; it doesn’t touch vault.stronghold.

Quick reference (paths & files)
pgsql
Copy
Edit
Documents/
└─ Stronghold/
   └─ <AccountName>/
      ├─ vault.stronghold      # encrypted keystore (critical)
      └─ rocksdb_storage/      # wallet cache/index (rebuildable)
If you remember one thing: Back up your mnemonic and vault.stronghold (plus the password). With those, you can always restore.
