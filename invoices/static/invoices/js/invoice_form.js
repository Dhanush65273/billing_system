// static/invoices/js/invoice_form.js

console.log("invoice_form.js loaded");

window.addEventListener("load", function () {
    // find all product selects
    const selects = document.querySelectorAll("select.product-select");
    console.log("found product selects:", selects.length);

    selects.forEach(function (select) {
        select.addEventListener("change", function () {
            const row = select.closest("tr");
            if (!row) return;

            const selectedOption = select.options[select.selectedIndex];
            const price = selectedOption.getAttribute("data-price") || "";

            // in each row: first input = quantity, second (last) = unit price
            const inputs = row.querySelectorAll("input");
            if (!inputs.length) {
                console.log("no inputs in row");
                return;
            }

            const unitPriceInput = inputs[inputs.length - 1];

            console.log("product changed", {
                productId: select.value,
                price: price,
                unitPriceInputName: unitPriceInput.name,
            });

            unitPriceInput.value = price;
        });
    });
});
