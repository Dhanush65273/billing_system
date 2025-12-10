// static/invoices/js/invoice_form.js

console.log("invoice_form.js loaded");

// attach auto-price handler to one select element
function attachPriceHandler(select) {
    if (!select) return;

    // avoid duplicate listeners
    if (select.__priceHandlerAttached) return;
    select.__priceHandlerAttached = true;

    select.addEventListener("change", function () {
        const row = select.closest("tr");
        if (!row) return;

        const selectedOption = select.options[select.selectedIndex];
        const price = selectedOption.getAttribute("data-price") || "";

        // ✅ find specifically the unit_price input in this row
        const unitPriceInput = row.querySelector('input[name$="-unit_price"]');

        if (!unitPriceInput) {
            console.log("unit_price input not found in row", row);
            return;
        }

        console.log("product changed", {
            productId: select.value,
            price: price,
            unitPriceInputName: unitPriceInput.name,
        });

        if (price !== "") {
            unitPriceInput.value = price;
        }
    });
}

function renumberRows() {
    const rows = document.querySelectorAll("#formset-body tr.item-row");
    let counter = 1;
    rows.forEach((row) => {
        if (row.style.display === "none") return;
        const numCell = row.querySelector(".row-number");
        if (numCell) {
            numCell.textContent = counter;
            counter += 1;
        }
    });
}

window.addEventListener("load", function () {
    // ----- 1. Auto price for EXISTING rows -----
    const selects = document.querySelectorAll("select.product-select");
    console.log("found product selects:", selects.length);
    selects.forEach(attachPriceHandler);

    // ----- 2. Dynamic rows: Add / Delete -----
    const tableBody = document.getElementById("formset-body");
    const addBtn = document.getElementById("add-row-btn");
    const templateEl = document.getElementById("empty-row");
    const totalFormsInput = document.querySelector('input[name$="-TOTAL_FORMS"]');

    if (!tableBody || !addBtn || !templateEl || !totalFormsInput) {
        console.log("Formset elements missing, dynamic rows disabled", {
            tableBody: !!tableBody,
            addBtn: !!addBtn,
            templateEl: !!templateEl,
            totalFormsInput: !!totalFormsInput,
        });
        return;
    }

    // ➕ Add item row
    addBtn.addEventListener("click", function (e) {
        e.preventDefault();
        console.log("Add item clicked");

        const formIndex = parseInt(totalFormsInput.value, 10) || 0;

        // replace __prefix__ & __num__ in template
        let rowHtml = templateEl.innerHTML
            .replace(/__prefix__/g, formIndex)
            .replace(/__num__/g, formIndex + 1);

        const temp = document.createElement("tbody");
        temp.innerHTML = rowHtml.trim();
        const newRow = temp.firstElementChild;

        tableBody.appendChild(newRow);

        // increase TOTAL_FORMS
        totalFormsInput.value = formIndex + 1;

        // attach price handler to new select
        const newSelect = newRow.querySelector("select.product-select");
        attachPriceHandler(newSelect);

        renumberRows();
    });

    // ❌ Delete row
    tableBody.addEventListener("click", function (e) {
        const btn = e.target.closest(".delete-row-btn");
        if (!btn) return;

        e.preventDefault();
        const row = btn.closest("tr.item-row");
        if (!row) return;

        const deleteField = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (deleteField) {
            deleteField.checked = true;  // tell Django to delete this form
        }

        row.style.display = "none";
        renumberRows();
    });
});
