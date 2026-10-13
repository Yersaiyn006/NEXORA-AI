from django import forms
from .models import BusinessProfile, CatalogItem


class CatalogForm(forms.ModelForm):
    class Meta:
        model = CatalogItem
        fields = ["kind", "name", "description", "price", "currency", "duration_minutes", "is_available"]
        labels = {"kind": "Тип", "name": "Название", "description": "Описание", "price": "Цена", "currency": "Валюта", "duration_minutes": "Длительность, мин.", "is_available": "Доступно"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def clean_price(self):
        value = self.cleaned_data["price"]
        if value is not None and value < 0:
            raise forms.ValidationError("Цена не может быть отрицательной.")
        return value

    def clean_duration_minutes(self):
        value = self.cleaned_data["duration_minutes"]
        if value is not None and not 1 <= value <= 1440:
            raise forms.ValidationError("Длительность: от 1 до 1440 минут.")
        return value

    def clean_currency(self):
        value = self.cleaned_data["currency"].upper()
        if value not in ("KZT", "USD", "EUR", "RUB"):
            raise forms.ValidationError("Выберите KZT, USD, EUR или RUB.")
        return value


class ProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = ["address", "working_hours", "delivery_info", "payment_info", "rules"]
        labels = {"address": "Адрес", "working_hours": "График работы", "delivery_info": "Доставка", "payment_info": "Способы оплаты", "rules": "Правила и условия"}
        widgets = {"delivery_info": forms.Textarea(attrs={"rows": 2}), "payment_info": forms.Textarea(attrs={"rows": 2}), "rules": forms.Textarea(attrs={"rows": 3})}
