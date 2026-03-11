from django import forms
from .models import RefundRequest

class RefundRequestForm(forms.ModelForm):
    class Meta:
        model = RefundRequest
        fields = ['order_id', 'amount', 'reason', 'details', 'proof_file']
