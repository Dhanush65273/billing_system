console.log("invoice_form.js loaded");

// ---------- helpers ----------
function parseNumber(value) {
    const n = parseFloat(value);
    return isNaN(n) ? 0 : n;
}

// map: productId -> price
function getPriceMap() {
    const el = document.getElementById("product-price-data");
    if (!el) return {};
    try {
        return JSON.parse(el.textContent.trim());
    } catch (e) {
        console.error("price json parse error", e);
        return {};
    }
}

const priceMap = getPriceMap();

// ---------- row setup ----------
function setupRow(row) {
    if (!row) return;

    const productSelect = row.querySelector("select");
    const qtyInput = row.querySelector('input[name$="-quantity"]');
    const unitPriceInput = row.querySelector('input[name$="-unit_price"]');

    // default qty = 1
    if (qtyInput && !qtyInput.value) {
        qtyInput.value = "1";
    }

    // when product changes -> fill unit price
    if (productSelect && unitPriceInput) {
        productSelect.addEventListener("change", function () {
            const pid = this.value;
            const price = priceMap[pid] ? parseNumber(priceMap[pid]) : 0;
            if (price) {
                unitPriceInput.value = price.toFixed(2);
            } else {
                unitPriceInput.value = "";
            }
            recalcTotals();
        });
    }

    // when qty or unit price changes -> recalc
    if (qtyInput) qtyInput.addEventListener("input", recalcTotals);
    if (unitPriceInput) unitPriceInput.addEventListener("input", recalcTotals);
}

// ---------- totals ----------
function recalcTotals() {
    const taxPercentInput = document.getElementById("id_tax_percent");
    const discountAmountInput = document.getElementById("id_discount_amount");

    const taxPercent = parseNumber(taxPercentInput ? taxPercentInput.value : 0);
    const invoiceDiscount = parseNumber(
        discountAmountInput ? discountAmountInput.value : 0
    );

    const rows = document.querySelectorAll(".invoice-item-row");

    let subtotal = 0;
    const lineSubtotals = [];

    // 1st pass: subtotal per row
    rows.forEach((row, idx) => {
        const qtyInput = row.querySelector('input[name$="-quantity"]');
        const unitPriceInput = row.querySelector('input[name$="-unit_price"]');

        const qty = parseNumber(qtyInput ? qtyInput.value : 0);
        const unitPrice = parseNumber(unitPriceInput ? unitPriceInput.value : 0);

        const lineSubtotal = qty * unitPrice;
        lineSubtotals[idx] = lineSubtotal;
        subtotal += lineSubtotal;
    });

    // 2nd pass: tax, discount, total per row
    let totalTax = 0;
    let totalDiscount = 0;
    let grandTotal = 0;

    rows.forEach((row, idx) => {
        const lineSubtotal = lineSubtotals[idx];

        // tax = subtotal * invoice tax %
        const lineTax = lineSubtotal * (taxPercent / 100.0);

        // discount distributed by proportion of subtotal
        const lineDiscount =
            subtotal > 0 ? (lineSubtotal / subtotal) * invoiceDiscount : 0;

        const lineTotal = lineSubtotal + lineTax - lineDiscount;

        const taxField = row.querySelector(".item-tax");
        const discountField = row.querySelector(".item-discount");
        const totalField = row.querySelector(".item-total");

        if (taxField) taxField.value = lineTax ? lineTax.toFixed(2) : "";
        if (discountField)
            discountField.value = lineDiscount ? lineDiscount.toFixed(2) : "";
        if (totalField) totalField.value = lineTotal ? lineTotal.toFixed(2) : "";

        totalTax += lineTax;
        totalDiscount += lineDiscount;
        grandTotal += lineTotal;
    });

    // footer inputs
    const subtotalInput = document.getElementById("subtotal");
    const totalTaxInput = document.getElementById("total-tax");
    const totalDiscountInput = document.getElementById("total-discount");
    const grandTotalInput = document.getElementById("grand-total");

    if (subtotalInput) subtotalInput.value = subtotal ? subtotal.toFixed(2) : "";
    if (totalTaxInput) totalTaxInput.value = totalTax ? totalTax.toFixed(2) : "";
    if (totalDiscountInput)
        totalDiscountInput.value = totalDiscount ? totalDiscount.toFixed(2) : "";
    if (grandTotalInput)
        grandTotalInput.value = grandTotal ? grandTotal.toFixed(2) : "";
}

// ---------- add / delete rows ----------
function renumberRows() {
    const rows = document.querySelectorAll(".invoice-item-row .row-index");
    rows.forEach((cell, idx) => {
        cell.textContent = idx + 1;
    });
}

function setupDeleteButtons() {
    document
        .querySelectorAll(".invoice-item-row .delete-row")
        .forEach((btn) => {
            btn.addEventListener("click", function () {
                const row = this.closest("tr");
                if (!row) return;
                row.remove();
                renumberRows();
                recalcTotals();
            });
        });
}

function addNewRow() {
    const tbody = document.getElementById("items-body");
    if (!tbody) return;

    const totalFormsInput = document.getElementById("id_items-TOTAL_FORMS");
    // if your management form name is different, adjust ^

    const currentCount = parseInt(totalFormsInput.value, 10) || 0;
    const emptyRowTemplate = tbody.querySelector("tr.invoice-item-row");
    if (!emptyRowTemplate) return;

    const newRow = emptyRowTemplate.cloneNode(true);

    // update form index in all name/id attributes
    newRow.querySelectorAll("[name], [id], [for]").forEach((el) => {
        ["name", "id", "for"].forEach((attr) => {
            const val = el.getAttribute(attr);
            if (val) {
                el.setAttribute(
                    attr,
                    val.replace(/items-\d+-/g, "items-" + currentCount + "-")
                );
            }
        });

        if (el.tagName === "INPUT") {
            const type = el.getAttribute("type") || "text";
            if (type === "text" || type === "number") {
                el.value = "";
            }
            if (type === "checkbox") {
                el.checked = false;
            }
        }
        if (el.tagName === "SELECT") {
            el.selectedIndex = 0;
        }
    });

    tbody.appendChild(newRow);
    totalFormsInput.value = currentCount + 1;

    setupRow(newRow);
    setupDeleteButtons();
    renumberRows();
    recalcTotals();
}

// ---------- init ----------
window.addEventListener("DOMContentLoaded", function () {
    // existing rows
    document.querySelectorAll(".invoice-item-row").forEach(setupRow);

    // recalc when header tax / discount changes
    const taxPercentInput = document.getElementById("id_tax_percent");
    const discountAmountInput = document.getElementById("id_discount_amount");
    if (taxPercentInput) taxPercentInput.addEventListener("input", recalcTotals);
    if (discountAmountInput)
        discountAmountInput.addEventListener("input", recalcTotals);

    // add item button
    const addBtn = document.getElementById("add-item");
    if (addBtn) addBtn.addEventListener("click", addNewRow);

    setupDeleteButtons();
    recalcTotals();
});
