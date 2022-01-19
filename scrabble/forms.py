from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    field_order = ['username', 'email', 'password1', 'password2']

    class Meta:
        model = User
        fields = {
            'username',
            'email',
            'password1',
            'password2'
        }

    def save(self, commit=True):
        user = super(RegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
