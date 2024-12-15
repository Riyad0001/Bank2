from django.db import models
from accounts.models import UserBankAccount
# Create your models here.
from .constants import TRANSACTION_TYPE

class Transaction(models.Model):
    account = models.ForeignKey(UserBankAccount, related_name = 'transactions', on_delete = models.CASCADE) # ekjon user er multiple transactions hote pare
    recipient_account=models.ForeignKey(UserBankAccount,null=True,blank=True,on_delete=models.CASCADE,related_name="recived_transaction")
    amount = models.DecimalField(decimal_places=2, max_digits = 12)
    balance_after_transaction = models.DecimalField(decimal_places=2, max_digits = 12)
    transaction_type = models.IntegerField(choices=TRANSACTION_TYPE, null = True)
    timestamp = models.DateTimeField(auto_now_add=True)
    loan_approve = models.BooleanField(default=False) 
    
    class Meta:
        ordering = ['timestamp']

class BankStatus(models.Model):
    transactions_enabled = models.BooleanField(default=True)

    def __str__(self):
        return "Transactions Enabled" if self.transactions_enabled else "Transactions Disabled" 