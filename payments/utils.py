# invoices/utils.py
from decimal import Decimal

def recalculate_invoice_totals(invoice):
    """
    Recalculate subtotal/total from invoice items.
    Defensive: tries common related names and fields so it won't break existing models.
    """
    items_manager = getattr(invoice, "items", None) or getattr(invoice, "invoiceitem_set", None)
    if items_manager is None:
        return

    try:
        qs = items_manager.all()
    except Exception:
        qs = items_manager

    subtotal = Decimal("0")
    for it in qs:
        item_total = getattr(it, "total", None)
        if item_total is None:
            qty = getattr(it, "quantity", None) or getattr(it, "qty", None) or 1
            price = getattr(it, "unit_price", None) or getattr(it, "price", 0) or 0
            item_total = Decimal(str(qty)) * Decimal(str(price))
        else:
            item_total = Decimal(str(item_total))
        subtotal += item_total

    # write subtotal if field exists
    if hasattr(invoice, "subtotal"):
        invoice.subtotal = subtotal

    discount = Decimal(str(getattr(invoice, "discount", 0) or 0))
    tax = Decimal(str(getattr(invoice, "tax", 0) or 0))
    total = subtotal - discount + tax

    if hasattr(invoice, "total"):
        invoice.total = total
    elif hasattr(invoice, "amount"):
        invoice.amount = total
    else:
        try:
            invoice.temp_total = total
        except Exception:
            pass

    invoice.save()