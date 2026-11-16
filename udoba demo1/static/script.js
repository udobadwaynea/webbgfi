
"use strict";

// BGFIBank is a front-end.

// Starting account balance.
const startingBalance = 10200000.00;

let balance = startingBalance;
let income = 0.00;
let expenses = 0.00;

const initialTransactions = [
];

let transactions = initialTransactions.map(item => ({ ...item }));

// Dashboard elements.
const balanceElement = document.getElementById("balance");
const incomeElement = document.getElementById("income");
const expensesElement = document.getElementById("expenses");
const transactionList = document.getElementById("transactionList");

// Modal elements.
const backdrop = document.getElementById("modalBackdrop");
const modalTitle = document.getElementById("modalTitle");
const modalDescription = document.getElementById("modalDescription");
const transferForm = document.getElementById("transferForm");
const recipientInput = document.getElementById("recipient");
const amountInput = document.getElementById("transferAmount");
const formError = document.getElementById("formError");
const submitAction = document.getElementById("submitAction");
const toast = document.getElementById("toast");

let currentAction = "transfer";
let showAllTransactions = false;
let toastTimeout;

// Format money as USD.
function formatMoney(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD"
  }).format(amount);
}

// Round money to two decimal places.
function roundMoney(amount) {
  return Math.round((amount + Number.EPSILON) * 100) / 100;
}

// Get today's date.
function getToday() {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC"
  }).format(new Date()).toUpperCase();
}

// Display a temporary notification.
function showToast(message) {
  if (!toast) return;

  toast.textContent = message;
  toast.classList.add("visible");

  clearTimeout(toastTimeout);

  toastTimeout = setTimeout(() => {
    toast.classList.remove("visible");
  }, 3500);
}

// Display transaction history.
function renderTransactions() {
  if (!transactionList) return;

  const visibleTransactions = showAllTransactions
    ? transactions
    : transactions.slice(0, 4);

  transactionList.replaceChildren();

  if (visibleTransactions.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");

    cell.colSpan = 4;
    cell.textContent = "No transactions yet.";

    row.appendChild(cell);
    transactionList.appendChild(row);
    return;
  }

  visibleTransactions.forEach(transaction => {
    const row = document.createElement("tr");

    const nameCell = document.createElement("td");

    const icon = document.createElement("span");
    icon.className = `merchant-icon ${transaction.color}`;
    icon.textContent = transaction.icon;

    const merchant = document.createElement("span");
    merchant.className = "merchant";

    const merchantName = document.createElement("span");
    merchantName.textContent = transaction.name;

    const category = document.createElement("small");
    category.textContent = transaction.category;

    merchant.append(merchantName, category);
    nameCell.append(icon, merchant);

    const dateCell = document.createElement("td");
    dateCell.textContent = transaction.date;

    const statusCell = document.createElement("td");

    const status = document.createElement("span");
    status.className = "status Cancelled";
    status.textContent = "Cancelled";

    statusCell.appendChild(status);

    const amountCell = document.createElement("td");
    amountCell.className = "amount";

    if (transaction.amount > 0) {
      amountCell.classList.add("positive-amount");
      amountCell.textContent = `+${formatMoney(transaction.amount)}`;
    } else {
      amountCell.textContent =
        `−${formatMoney(Math.abs(transaction.amount))}`;
    }

    row.append(nameCell, dateCell, statusCell, amountCell);
    transactionList.appendChild(row);
  });

  const viewAllButton = document.getElementById("viewAllButton");

  if (viewAllButton) {
    viewAllButton.textContent = showAllTransactions
      ? "Show less ↑"
      : "View all →";
  }
}

// Refresh dashboard figures.
function renderDashboard() {
  if (balanceElement) {
    balanceElement.textContent = formatMoney(balance);
  }

  if (incomeElement) {
    incomeElement.textContent = formatMoney(income);
  }

  if (expensesElement) {
    expensesElement.textContent = formatMoney(expenses);
  }

  renderTransactions();
}

// Open the transfer or deposit modal.
function openModal(action) {
  if (!backdrop || !transferForm) return;

  currentAction = action;
  formError.textContent = "";
  transferForm.reset();

  if (action === "transfer") {
    modalTitle.textContent = "Transfer funds";
    modalDescription.textContent = "Sending funds to a recipient.";
    submitAction.textContent = "Simulate transfer";

    recipientInput.required = true;
    recipientInput.disabled = false;
  } else {
    modalTitle.textContent = "Add funds";
    modalDescription.textContent =
      "Increase your balance for testing. This does not deposit real money.";

    submitAction.textContent = "Add funds";

    recipientInput.required = false;
    recipientInput.disabled = true;
  }

  backdrop.hidden = false;
  document.body.style.overflow = "hidden";

  if (action === "transfer") {
    recipientInput.focus();
  } else {
    amountInput.focus();
  }
}

// Close the modal.
function closeModal() {
  if (!backdrop) return;

  backdrop.hidden = true;
  document.body.style.overflow = "";

  if (formError) {
    formError.textContent = "";
  }
}

// Add a transaction to the history.
function addTransaction(name, category, amount, type, icon, color) {
  transactions.unshift({
    name,
    category,
    date: getToday(),
    amount,
    type,
    icon,
    color
  });
}

// Transfer button.
const transferButton = document.getElementById("transferButton");

if (transferButton) {
  transferButton.addEventListener("click", () => {
    window.location.href = "/transfer";
  });
}

// Deposit button.
const depositButton = document.getElementById("depositButton");

if (depositButton) {
  depositButton.addEventListener("click", () => {
    openModal("deposit");
  });
}

// Close button.
const closeModalButton = document.getElementById("closeModal");

if (closeModalButton) {
  closeModalButton.addEventListener("click", closeModal);
}

// Close modal when clicking outside it.
if (backdrop) {
  backdrop.addEventListener("click", event => {
    if (event.target === backdrop) {
      closeModal();
    }
  });
}

// Close modal with Escape.
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && backdrop && !backdrop.hidden) {
    closeModal();
  }
});

// Handle deposits and simulated transfers.
if (transferForm) {
  transferForm.addEventListener("submit", event => {
    event.preventDefault();

    const amount = Number(amountInput.value);
    const recipient = recipientInput.value.trim();

    if (!Number.isFinite(amount) || amount <= 0 || amount > 1000000) {
      formError.textContent =
        "Enter an amount greater than zero and no more than $1,000,000.";
      return;
    }

    if (currentAction === "transfer") {
      if (!recipient || recipient.length > 50) {
        formError.textContent = "Enter a valid recipient name.";
        return;
      }

      if (amount > balance) {
        formError.textContent =
          "Insufficient balance. Try a smaller amount.";
        return;
      }

      balance = roundMoney(balance - amount);
      expenses = roundMoney(expenses + amount);

      addTransaction(
        `Transfer to ${recipient}`,
        "Outgoing transfer",
        -amount,
        "expense",
        "T",
        "blue"
      );

      renderDashboard();
      closeModal();

      showToast(`Simulated transfer of ${formatMoney(amount)}.`);
    } else {
      balance = roundMoney(balance + amount);
      income = roundMoney(income + amount);

      addTransaction(
        "Funds added",
        "Deposit",
        amount,
        "income",
        "+",
        "green"
      );

      renderDashboard();
      closeModal();

      showToast(`${formatMoney(amount)} added to the account.`);
    }
  });
}

// View all transactions.
const viewAllButton = document.getElementById("viewAllButton");

if (viewAllButton) {
  viewAllButton.addEventListener("click", () => {
    showAllTransactions = !showAllTransactions;
    renderTransactions();
  });
}

// Display the transaction statement.
const statementButton = document.getElementById("statementButton");

if (statementButton) {
  statementButton.addEventListener("click", () => {
    showAllTransactions = true;
    renderTransactions();

    const transactionsSection = document.getElementById("transactions");

    if (transactionsSection) {
      transactionsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    }

    showToast("Showing your transaction statement.");
  });
}

// Mobile navigation.
const menuButton = document.getElementById("menuButton");
const sidebar = document.getElementById("sidebar");

if (menuButton && sidebar) {
  menuButton.addEventListener("click", () => {
    const isOpen = sidebar.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
  });

  document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
      document.querySelectorAll(".nav-link").forEach(item => {
        item.classList.remove("active");
      });

      link.classList.add("active");
      sidebar.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
    });
  });
}

// Update the live clock and date.
function updateBGFIClock() {
  const timeElement = document.getElementById("live-time");
  const dateElement = document.getElementById("live-date");

  if (!timeElement || !dateElement) return;

  const now = new Date();

  timeElement.textContent = now.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });

  dateElement.textContent = now.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric"
  });
}

// Rotate the dashboard logos.
const dashboardLogos = [
  "bgfi1.jpg",
  "bgfi2.jpg",
  "bgfi3.jpg",
  "bgfi4.jpg",
  "bgfi5.jpg",
  "bgfi6.jpg",
  "bgfi7.jpg"
];

const rotatingLogo = document.getElementById("dashboardRotatingLogo");

if (rotatingLogo) {
  let currentLogoIndex = 0;

  setInterval(() => {
    currentLogoIndex = (currentLogoIndex + 1) % dashboardLogos.length;

    rotatingLogo.src = `/static/${dashboardLogos[currentLogoIndex]}`;
    rotatingLogo.alt = `BGFIBank logo ${currentLogoIndex + 1}`;
  }, 3000);
}

// Start the dashboard.
renderDashboard();
updateBGFIClock();

setInterval(updateBGFIClock, 1000);
