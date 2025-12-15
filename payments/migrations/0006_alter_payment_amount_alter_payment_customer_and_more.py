from django.db import migrations, models
import django.db.models.deletion


def set_customer_from_invoice(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    # iterate - for small DB this is fine; for huge DB use batching
    for p in Payment.objects.all():
        if getattr(p, "invoice_id", None):
            try:
                # assign by id to avoid extra query
                p.customer_id = p.invoice.customer_id
                p.save(update_fields=["customer_id"])
            except Exception:
                # skip problematic rows; log in real app if needed
                continue


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        ('invoices', '0001_initial'),
        ('payments', '0005_alter_payment_amount_alter_payment_customer_and_more'),  # <- EXACT previous migration name
    ]

    operations = [
        # 1) Add the new field as nullable so DB allows existing rows.
        migrations.AddField(
            model_name='payment',
            name='customer',
            field=models.ForeignKey(
                to='customers.customer',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments',
                null=True,
                blank=True,
            ),
        ),
        # 2) Populate the new field from invoice -> customer for existing rows
        migrations.RunPython(set_customer_from_invoice, reverse_code=migrations.RunPython.noop),
        # 3) Make the field required (non-nullable) in final state
        migrations.AlterField(
            model_name='payment',
            name='customer',
            field=models.ForeignKey(
                to='customers.customer',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='payments',
                null=False,
            ),
        ),
    ]
