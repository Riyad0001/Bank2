from .models import BankStatus

def are_transactions_enabled():
    status = BankStatus.objects.first()
    return status.transactions_enabled if status else True
