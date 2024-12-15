from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse,HttpResponseForbidden
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID,TRANSFER_MONEY
from datetime import datetime
from django.db.models import Sum
from django.shortcuts import render
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm,
)
from transactions.models import Transaction
from .utils import are_transactions_enabled
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.template.loader import render_to_string


def transaction_mail_send(user,subject,amount,template):
    message=render_to_string(template,{'user':user,'amount':amount})
    send_mail=EmailMultiAlternatives(subject,'',to=[user.email])
    send_mail.attach_alternative(message,"text/html")
    send_mail.send()
    


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context
    def dispatch(self, request, *args, **kwargs):
        if not are_transactions_enabled():
            messages.error(request, "Bank is bankrupt. Transactions are disabled.")
            return HttpResponseForbidden("Bank is bankrupt. Transactions are disabled.")
        return super().dispatch(request, *args, **kwargs)


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        transaction_mail_send(self.request.user,"Deposite MAil",amount,'transactions/deposite_email.html')

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')

        self.request.user.account.balance -= form.cleaned_data.get('amount')
        # balance = 300
        # amount = 5000
        self.request.user.account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )
        transaction_mail_send(self.request.user,"Withdrawal Mail",amount,'transactions/withdrawal_email.html')

        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )
        transaction_mail_send(self.request.user,"Loan Request Mail",amount,'transactions/loan_email.html')

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
                # Reduce the loan amount from the user's balance
                # 5000, 500 + 5000 = 5500
                # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')
    def dispatch(self, request, *args, **kwargs):
        if not are_transactions_enabled():
            messages.error(request, "Bank is bankrupt. Transactions are disabled.")
            return HttpResponseForbidden("Bank is bankrupt. Transactions are disabled.")
        return super().dispatch(request, *args, **kwargs)


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset


class TransferMoneyView(LoginRequiredMixin, View):
    def get(self, request):
        form = TransferForm(account=request.user.account)
        return render(request, 'transactions/transfer_form.html', {'form': form, 'title': 'Transfer Money'})

    def get_initial(self):
        initial = {'transaction_type': TRANSFER_MONEY}
        return initial
    def dispatch(self, request, *args, **kwargs):
        if not are_transactions_enabled():
            messages.error(request, "Bank is bankrupt. Transactions are disabled.")
            return HttpResponseForbidden("Bank is bankrupt. Transactions are disabled.")
        return super().dispatch(request, *args, **kwargs)
    def post(self, request):
        form = TransferForm(request.POST, account=request.user.account)
        if form.is_valid():
            sender = request.user.account
            recipient = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']

            try:
                # Deduct from sender's account
                sender.balance -= amount
                sender.save(update_fields=['balance'])

                # Add to recipient's account
                recipient.balance += amount
                recipient.save(update_fields=['balance'])

                # Log the transaction
                Transaction.objects.create(
                    account=sender,
                    recipient_account=recipient,
                    transaction_type=5,  # Assuming 5 represents Transfer
                    amount=amount,
                    balance_after_transaction=sender.balance  # Pass the sender's balance after the transaction
                )

                messages.success(
                    request, f'Successfully transferred ${amount:.2f} to {recipient.user.username}'
                )
                transaction_mail_send(self.request.user,"Transfer Money Mail",amount,'transactions/tsender_email.html')
                transaction_mail_send(recipient.user,"Recive Money Mail",amount,'transactions/treciver_email.html')
                return redirect('transaction_report')

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
                return render(request, 'transactions/transfer_form.html', {'form': form, 'title': 'Transfer Money'})

        # If form is invalid, re-render with error messages
        messages.error(request, "Failed to complete the transfer. Please correct the errors below.")
        return render(request, 'transactions/transfer_form.html', {'form': form, 'title': 'Transfer Money'})

