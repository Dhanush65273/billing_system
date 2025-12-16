console.log("FINAL invoice JS – PRICE + TOTAL FIXED");

function num(v) {
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
}

// 🔥 PRICE AUTO FILL
function attachProductPrice(row) {
    const select = row.querySelector(".product-select");
    if (!select || select.__bound) return;
    select.__bound = true;

    select.addEventListener("change", () => {
        const opt = select.options[select.selectedIndex];
        const price = opt?.getAttribute("data-price");

        const priceInput = row.querySelector('[name$="-unit_price"]');
        if (price && priceInput) {
            priceInput.value = price;
        }
        recalcTotals();
    });
}

function recalcTotals() {
    let grand = 0;

    document.querySelectorAll("#formset-body tr.item-row").forEach(row => {
        if (row.style.display === "none") return;

        const qty = num(row.querySelector('[name$="-quantity"]')?.value);
        const price = num(row.querySelector('[name$="-unit_price"]')?.value);
        const taxP = num(row.querySelector('[name$="-tax_percent"]')?.value);
        const dType = row.querySelector('[name$="-discount_type"]')?.value;
        const dVal = num(row.querySelector('[name$="-discount_value"]')?.value);

        let subtotal = qty * price;
        let discount = dType === "percent" ? subtotal * dVal / 100 : dVal;
        let taxable = Math.max(subtotal - discount, 0);
        let tax = taxable * taxP / 100;
        let total = taxable + tax;

        const totalField = row.querySelector(".item-total");
        if (totalField) totalField.value = total.toFixed(2);

        grand += total;
    });

    const gt = document.getElementById("grand-total");
    if (gt) gt.value = grand.toFixed(2);
}

document.addEventListener("DOMContentLoaded", () => {

    const body = document.getElementById("formset-body");
    const addBtn = document.getElementById("add-row-btn");
    const tpl = document.getElementById("empty-row");
    const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');

    // 🔥 existing rows
    body.querySelectorAll("tr.item-row").forEach(row => {
        attachProductPrice(row);
    });

    addBtn.addEventListener("click", e => {
        e.preventDefault();

        const index = parseInt(totalForms.value, 10);

        let html = tpl.innerHTML
            .replace(/__prefix__/g, index)
            .replace(/__num__/g, index + 1);

        const temp = document.createElement("tbody");
        temp.innerHTML = html.trim();
        const row = temp.firstElementChild;

        body.appendChild(row);
        totalForms.value = index + 1;

        attachProductPrice(row);
        recalcTotals();
    });

    body.addEventListener("input", recalcTotals);
    body.addEventListener("change", recalcTotals);

    body.addEventListener("click", e => {
        if (e.target.classList.contains("delete-row-btn")) {
            const row = e.target.closest("tr");
            const del = row.querySelector('[name$="-DELETE"]');
            if (del) del.checked = true;
            row.style.display = "none";
            recalcTotals();
        }
    });

    recalcTotals();
});
