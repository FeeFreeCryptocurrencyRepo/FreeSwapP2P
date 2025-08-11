const API_BASE = `${location.origin}/api`; // e.g., http://localhost:5000/api

// ------------------ Elements ------------------
const loginCard = document.getElementById("loginCard");
const walletCard = document.getElementById("walletCard");

const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const loginMethodEl = document.getElementById("loginMethod");
const privateKeyRow = document.getElementById("privateKeyRow");
const privateKeyEl = document.getElementById("privateKey");
const confirmRow = document.getElementById("confirmRow");
const password2El = document.getElementById("password2");
const mnemonicRow = document.getElementById("mnemonicRow");
const createdMnemonicEl = document.getElementById("createdMnemonic");
const copyMnemonicBtn = document.getElementById("copyMnemonicBtn");

const loginErrorEl = document.getElementById("loginError");
const loginProgress = document.getElementById("loginProgress");

const loginBtn = document.getElementById("loginBtn");
const clearBtn = document.getElementById("clearBtn");
const logoutBtn = document.getElementById("logoutBtn");

const balanceEl = document.getElementById("balance");
const refreshBtn = document.getElementById("refreshBtn");

const popupBtn = document.getElementById("popupBtn");
const modalBackdrop = document.getElementById("modalBackdrop");
const closePopupBtn = document.getElementById("closePopupBtn");

const showSendBtn = document.getElementById("showSendBtn");
const showReceiveBtn = document.getElementById("showReceiveBtn");

const sendView = document.getElementById("sendView");
const receiveView = document.getElementById("receiveView");

const recipientEl = document.getElementById("recipient");
const amountEl = document.getElementById("amount");
const sendBtn = document.getElementById("sendBtn");
const sendErrorEl = document.getElementById("sendError");
const sendProgress = document.getElementById("sendProgress");

const myAddressEl = document.getElementById("myAddress");
const copyBtn = document.getElementById("copyBtn");
const receiveProgress = document.getElementById("receiveProgress");

// ------------------ State ------------------
let session = {
    token: null,
    account_name: null,
    pin: null,
    password: null,
};

// ------------------ Helpers ------------------
function setProgress(barEl, pct) {
    barEl.style.width = `${Math.max(0, Math.min(100, pct))}%`;
}

function show(el) { el.classList.remove("hidden"); }
function hide(el) { el.classList.add("hidden"); }

function isValidSmrAddress(addr) {
    const re = /^smr1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{59}$/;
    return re.test(addr);
}

async function api(path, options = {}) {
    const headers = options.headers || {};
    if (session.token) headers["Authorization"] = `Bearer ${session.token}`;
    return fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { "Content-Type": "application/json", ...headers },
    });
}

function toMicros(amountStr) {
    const v = Number(amountStr);
    if (!isFinite(v)) throw new Error("Invalid amount");
    return Math.round(v * 1_000_000);
}

function formatSmrMicros(micros) {
    return (Number(micros) / 1_000_000).toFixed(6);
}

function setLoginButtonLabel() {
    const m = loginMethodEl.value;
    loginBtn.textContent =
        m === "Create Account" ? "Create Account" :
            m === "Enter Private Key" ? "Login (Private Key)" :
                "Login";
}

// ------------------ UI Wiring ------------------
loginMethodEl.addEventListener("change", () => {
    const m = loginMethodEl.value;
    setLoginButtonLabel();

    if (m === "Enter Private Key") {
        show(privateKeyRow);
        hide(confirmRow);
        hide(mnemonicRow);
    } else if (m === "Create Account") {
        hide(privateKeyRow);
        show(confirmRow);
        hide(mnemonicRow);
    } else { // "Log in with PIN"
        hide(privateKeyRow);
        hide(confirmRow);
        hide(mnemonicRow);
    }
});

clearBtn.addEventListener("click", () => {
    usernameEl.value = "";
    passwordEl.value = "";
    password2El.value = "";
    privateKeyEl.value = "";
    createdMnemonicEl.value = "";
    hide(mnemonicRow);
    loginErrorEl.textContent = "";
    setProgress(loginProgress, 0);
});

loginBtn.addEventListener("click", async () => {
    loginErrorEl.textContent = "";
    setProgress(loginProgress, 25);

    const account_name = usernameEl.value.trim();
    const password = passwordEl.value;
    const pin = account_name; // mirrors your original behavior
    const method = loginMethodEl.value;
    const mnemonic = privateKeyEl.value.trim();

    if (!account_name || !password) {
        loginErrorEl.textContent = "Username and password are required.";
        setProgress(loginProgress, 0);
        return;
    }

    try {
        if (method === "Create Account") {
            // validate confirm password
            if (password !== password2El.value) {
                throw new Error("Passwords do not match.");
            }
            setProgress(loginProgress, 50);
            const res = await api("/create", {
                method: "POST",
                body: JSON.stringify({ account_name, password }),
            });
            if (!res.ok) throw new Error(await res.text() || "Create account failed.");

            const data = await res.json();
            const mnem = data.mnemonic || "";
            // show mnemonic, and pre-fill private key field for a natural login
            createdMnemonicEl.value = mnem;
            privateKeyEl.value = mnem;

            show(mnemonicRow);
            loginMethodEl.value = "Enter Private Key";
            setLoginButtonLabel();
            show(privateKeyRow);
            hide(confirmRow);

            loginErrorEl.textContent = "Account created. Save your mnemonic, then log in using 'Enter Private Key'.";
            return; // stop here; user will click Login again to recover+login
        }

        // Normal login flows
        let res;
        if (method === "Enter Private Key") {
            if (!mnemonic) throw new Error("Please paste your Private Key / mnemonic.");
            setProgress(loginProgress, 45);
            res = await api("/recover", { method: "POST", body: JSON.stringify({ account_name, pin, password, mnemonic }) });
            if (!res.ok) throw new Error(await res.text() || "Wallet recovery failed.");
            setProgress(loginProgress, 60);
            res = await api("/login", { method: "POST", body: JSON.stringify({ account_name, pin, password }) });
        } else {
            res = await api("/login", { method: "POST", body: JSON.stringify({ account_name, pin, password }) });
        }

        if (!res.ok) {
            const msg = await res.text();
            throw new Error(msg || "Login failed.");
        }

        const data = await res.json();
        session = { ...session, token: data.token || null, account_name, pin, password };

        hide(loginCard);
        show(walletCard);
        await refreshBalance();
    } catch (e) {
        loginErrorEl.textContent = e.message || "Login failed.";
    } finally {
        setProgress(loginProgress, 100);
        setTimeout(() => setProgress(loginProgress, 0), 400);
    }
});

logoutBtn.addEventListener("click", async () => {
    try {
        await api("/logout", { method: "POST" });
    } catch { }
    session = { token: null, account_name: null, pin: null, password: null };
    hide(walletCard);
    show(loginCard);
    // clear sensitive fields
    privateKeyEl.value = "";
    createdMnemonicEl.value = "";
    hide(mnemonicRow);
    passwordEl.value = "";
    password2El.value = "";
});

popupBtn.addEventListener("click", () => show(modalBackdrop));
closePopupBtn.addEventListener("click", () => hide(modalBackdrop));
modalBackdrop.addEventListener("click", (e) => {
    if (e.target === modalBackdrop) hide(modalBackdrop);
});

showSendBtn.addEventListener("click", () => {
    show(sendView);
    hide(receiveView);
    sendErrorEl.textContent = "";
});

showReceiveBtn.addEventListener("click", async () => {
    hide(sendView);
    show(receiveView);
    await loadMyAddress();
});

copyBtn.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(myAddressEl.value || "");
    } catch {
        myAddressEl.select();
        document.execCommand("copy");
    }
});

copyMnemonicBtn.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(createdMnemonicEl.value || "");
    } catch {
        createdMnemonicEl.select();
        document.execCommand("copy");
    }
});

refreshBtn.addEventListener("click", refreshBalance);

sendBtn.addEventListener("click", async () => {
    sendErrorEl.textContent = "";
    setProgress(sendProgress, 25);
    try {
        const recipient = recipientEl.value.trim();
        const amountStr = amountEl.value.trim();
        if (!isValidSmrAddress(recipient)) throw new Error("Invalid recipient address format.");
        const amountMicros = toMicros(amountStr);

        setProgress(sendProgress, 55);
        const res = await api("/send", {
            method: "POST",
            body: JSON.stringify({ recipient, amount: amountMicros }),
        });
        if (!res.ok) throw new Error(await res.text() || "Transaction failed.");
        const data = await res.json();
        alert(`Transaction successful! Sent ${formatSmrMicros(data.amount)} SMR.\nTX: ${data.txid || "(unknown)"}`);
        recipientEl.value = "";
        amountEl.value = "";
        await refreshBalance();
    } catch (e) {
        sendErrorEl.textContent = e.message || "Error sending transaction.";
    } finally {
        setProgress(sendProgress, 100);
        setTimeout(() => setProgress(sendProgress, 0), 400);
    }
});

// ------------------ Data Ops ------------------
async function refreshBalance() {
    setProgress(loginProgress, 30);
    try {
        const res = await api("/balance");
        if (!res.ok) throw new Error(await res.text() || "Balance fetch failed.");
        const data = await res.json();
        const asMicros = typeof data.available === "number" ? data.available : Number(data.available);
        const display = isFinite(asMicros) ? `${formatSmrMicros(asMicros)} SMR` : `${data.available}`;
        balanceEl.textContent = `Balance: ${display}`;
    } catch (e) {
        balanceEl.textContent = "Balance: 0 SMR";
        console.error(e);
    } finally {
        setProgress(loginProgress, 0);
    }
}

async function loadMyAddress() {
    setProgress(receiveProgress, 40);
    try {
        const res = await api("/address");
        if (!res.ok) throw new Error(await res.text() || "Address fetch failed.");
        const data = await res.json();
        myAddressEl.value = data.address || "";
    } catch (e) {
        myAddressEl.value = "";
        console.error(e);
    } finally {
        setProgress(receiveProgress, 100);
        setTimeout(() => setProgress(receiveProgress, 0), 400);
    }
}

// Init
setLoginButtonLabel();
