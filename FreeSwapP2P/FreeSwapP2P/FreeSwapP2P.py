# C:\Users\<User>\source\repos\FreeSwapP2P\FreeSwapP2P\FreeSwapP2P.py

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from pathlib import Path
import secrets
import re

# ---- Your wallet functions (must be in the same folder) ----
from IotaWallet import (
    SignInToAccount,
    RecoverWallet,
    CreateWallet,                 # ← new import
    get_my_balance,
    parse_available_balance,
    get_my_address_instanced,
    send_transaction,
)

APP_TITLE = "FreeSwapP2P"
API_PREFIX = "/api"

app = FastAPI(title=APP_TITLE)

# ---- CORS for LAN dev (tighten in prod) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # e.g., ["http://192.168.1.50:5000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Static files (optional): http://localhost:5000/web/index.html ----
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

# Convenience redirects and favicon
@app.get("/")
def root():
    return RedirectResponse(url="/web/index.html")

@app.get("/web")
def web_root():
    return RedirectResponse(url="/web/index.html")

@app.get("/favicon.ico")
def favicon():
    ico = WEB_DIR / "assets" / "icons" / "favicon.ico"
    if ico.exists():
        return FileResponse(str(ico))
    raise HTTPException(404, "favicon not found")

# -------------------- Models --------------------
class LoginRequest(BaseModel):
    account_name: str = Field(..., min_length=1)
    pin: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class RecoverRequest(LoginRequest):
    mnemonic: str = Field(..., min_length=1)

class CreateRequest(BaseModel):              # ← for Create Account
    account_name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class SendRequest(BaseModel):
    recipient: str
    amount: int  # micro-SMR (1 SMR = 1_000_000 micros)

# -------------------- Session (in-memory) --------------------
# token -> {"wallet": obj, "account_name": str, "pin": str, "password": str}
_SESSIONS: Dict[str, Dict[str, Any]] = {}

def _auth(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    token = authorization.split()[1]
    sess = _SESSIONS.get(token)
    if not sess:
        raise HTTPException(401, "Invalid or expired session")
    return sess

# -------------------- Utils --------------------
_SMR_ADDR_RE = re.compile(r"^smr1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{59}$")

def _parse_balance_to_micros(raw) -> int:
    try:
        parsed = parse_available_balance(str(raw))
        val = float(parsed)
        return int(round(val * 1_000_000))
    except Exception:
        if isinstance(raw, (int, float)):
            return int(round(raw))
        return 0

# -------------------- Routes --------------------
@app.post(f"{API_PREFIX}/login")
def login(body: LoginRequest):
    wallet, account = SignInToAccount(body.account_name, body.pin, body.password)
    if not wallet or not account:
        raise HTTPException(401, "Invalid credentials or account not found")
    token = secrets.token_urlsafe(32)
    _SESSIONS[token] = {
        "wallet": wallet,
        "account_name": body.account_name,
        "pin": body.pin,
        "password": body.password,
    }
    return {"token": token, "account": str(account)}

@app.post(f"{API_PREFIX}/recover")
def recover(body: RecoverRequest):
    ok = RecoverWallet(body.account_name, body.pin, body.password, body.mnemonic)
    if not ok:
        raise HTTPException(400, "Wallet recovery failed")
    return {"ok": True}

@app.post(f"{API_PREFIX}/create")            # ← Create Account
def create_account(body: CreateRequest):
    try:
        # CreateWallet(NameYourAccount, Password, Password) returns str(mnemonic)
        mnemonic = CreateWallet(body.account_name, body.password, body.password)
        return {"mnemonic": str(mnemonic)}
    except Exception as e:
        raise HTTPException(400, f"Create account failed: {e}")

@app.post(f"{API_PREFIX}/logout")            # ← Logout: kill session
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split()[1]
        _SESSIONS.pop(token, None)
    return {"ok": True}

@app.get(f"{API_PREFIX}/balance")
def balance(sess: Dict[str, Any] = Depends(_auth)):
    try:
        raw = get_my_balance(sess["wallet"], sess["pin"]) or 0
        micros = _parse_balance_to_micros(raw)
        return {"available": micros}
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch balance: {e}")

@app.get(f"{API_PREFIX}/address")
def address(sess: Dict[str, Any] = Depends(_auth)):
    try:
        addr = get_my_address_instanced(
            sess["wallet"], sess["account_name"], sess["pin"], sess["password"]
        )
        if not addr:
            raise HTTPException(404, "Address not found")
        return {"address": addr}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch address: {e}")

@app.post(f"{API_PREFIX}/send")
def send(body: SendRequest, sess: Dict[str, Any] = Depends(_auth)):
    if body.amount <= 0:
        raise HTTPException(400, "Amount must be > 0 (micro-SMR)")
    if not _SMR_ADDR_RE.match(body.recipient):
        raise HTTPException(400, "Invalid recipient address format")
    try:
        tx = send_transaction(sess["wallet"], sess["pin"], body.recipient, int(body.amount))
        txid = getattr(tx, "id", None) or getattr(tx, "transactionId", None) or getattr(tx, "hash", None)
        sent_amt = getattr(tx, "amount", body.amount)
        return {"txid": txid, "amount": int(sent_amt)}
    except Exception as e:
        raise HTTPException(500, f"Transaction failed: {e}")

# -------------------- Dev server --------------------
if __name__ == "__main__":
    # pip install fastapi uvicorn
    import uvicorn
    uvicorn.run("FreeSwapP2P:app", host="0.0.0.0", port=5000, reload=True)
