from django.contrib import admin
from .views import transaction_mail_send
# from transactions.models import Transaction
from .models import Transaction,BankStatus
admin.site.register(BankStatus)
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'amount', 'balance_after_transaction', 'transaction_type', 'loan_approve']
    
    def save_model(self, request, obj, form, change):
        obj.account.balance += obj.amount
        obj.balance_after_transaction = obj.account.balance
        obj.account.save()
        transaction_mail_send(obj.account.user,"Loan Approval",obj.amount,'transactions/admin_email.html')
        super().save_model(request, obj, form, change)

