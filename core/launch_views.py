"""Operator -> invitation -> business owner -> configured public consultant."""
import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal
from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from business_brain.models import BusinessProfile, CatalogItem
from core.models import Business, Membership, BusinessInvitation


def digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InviteForm(forms.Form):
    name = forms.CharField(label="Название компании", max_length=150)
    industry = forms.CharField(label="Сфера бизнеса", max_length=100)
    email = forms.EmailField(label="Email владельца")


class OwnerForm(forms.Form):
    def __init__(self, *args, invited_email="", **kwargs):
        super().__init__(*args, **kwargs)
        self.invited_email = invited_email

    username = forms.CharField(label="Логин", max_length=150)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password_repeat = forms.CharField(label="Повторите пароль", widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Такой логин уже занят.")
        return username

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("password_repeat"):
            self.add_error("password_repeat", "Пароли не совпадают.")
        elif data.get("password"):
            try:
                validate_password(data["password"], user=get_user_model()(username=data.get("username", ""), email=self.invited_email))
            except ValidationError as exc:
                self.add_error("password", exc)
        return data


class SetupForm(forms.Form):
    name = forms.CharField(label="Название", max_length=150)
    industry = forms.CharField(label="Сфера деятельности", max_length=100)
    description = forms.CharField(label="Чем занимается компания", widget=forms.Textarea(attrs={"rows": 3}), max_length=2000)
    phone = forms.CharField(label="Контактный телефон", max_length=30, required=False)
    address = forms.CharField(label="Адрес", max_length=250, required=False)
    working_hours = forms.CharField(label="График работы", max_length=300, required=False)
    delivery_info = forms.CharField(label="Доставка", widget=forms.Textarea(attrs={"rows": 2}), required=False)
    payment_info = forms.CharField(label="Способы оплаты", widget=forms.Textarea(attrs={"rows": 2}), required=False)
    rules = forms.CharField(label="Правила и условия", widget=forms.Textarea(attrs={"rows": 2}), required=False)


class QuickItemForm(forms.Form):
    kind = forms.ChoiceField(label="Тип", choices=CatalogItem.KINDS)
    name = forms.CharField(label="Название", max_length=180)
    price = forms.DecimalField(label="Цена, ₸", max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False)
    description = forms.CharField(label="Описание", max_length=1500, required=False)


def operator_only(user):
    if not user.is_staff:
        raise PermissionDenied("Только оператор NEXORA может создавать приглашения.")


def owner_business(request, business_id):
    member = get_object_or_404(Membership.objects.select_related("business"), user=request.user, business_id=business_id)
    if member.role not in ("owner", "admin"):
        raise PermissionDenied
    return member.business


@login_required

def launch_home(request):
    return render(request, "core/launch.html", {
        "screen": "home", "operator": request.user.is_staff,
        "businesses": Business.objects.filter(memberships__user=request.user).distinct().order_by("name"),
        "form": InviteForm(),
    })


@login_required
@require_POST
def create_invite(request):
    operator_only(request.user)
    form = InviteForm(request.POST)
    if not form.is_valid():
        return render(request, "core/launch.html", {"screen": "home", "operator": True, "form": form, "businesses": []}, status=400)
    with transaction.atomic():
        business = Business.objects.create(name=form.cleaned_data["name"], industry=form.cleaned_data["industry"], public_chat_enabled=False)
        token = secrets.token_urlsafe(32)
        BusinessInvitation.objects.create(business=business, email=form.cleaned_data["email"], token_hash=digest(token), expires_at=timezone.now() + timedelta(days=7))
    link = request.build_absolute_uri(reverse("launch_accept", args=[token]))
    return render(request, "core/launch.html", {"screen": "invitation", "business": business, "invite_link": link, "email": form.cleaned_data["email"]})


def accept_invite(request, token):
    invite = BusinessInvitation.objects.select_related("business").filter(token_hash=digest(token)).first()
    if not invite or not invite.is_valid():
        return render(request, "core/launch.html", {"screen": "expired"}, status=410)
    if request.user.is_authenticated:
        return render(request, "core/launch.html", {"screen": "logout_first", "business": invite.business}, status=403)
    form = OwnerForm(request.POST or None, invited_email=invite.email)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        user = User(username=form.cleaned_data["username"], email=invite.email)
        user.set_password(form.cleaned_data["password"])
        try:
            with transaction.atomic():
                claimed = BusinessInvitation.objects.filter(pk=invite.pk, used_at__isnull=True, expires_at__gt=timezone.now()).update(used_at=timezone.now())
                if not claimed:
                    return render(request, "core/launch.html", {"screen": "expired"}, status=410)
                if User.objects.filter(username__iexact=user.username).exists():
                    raise IntegrityError("username occupied")
                user.save()
                Membership.objects.create(user=user, business=invite.business, role="owner")
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("launch_setup", business_id=invite.business_id)
        except IntegrityError:
            form.add_error("username", "Такой логин уже занят. Выберите другой.")
    return render(request, "core/launch.html", {"screen": "accept", "business": invite.business, "form": form})


@login_required
def setup(request, business_id):
    business = owner_business(request, business_id)
    profile, _ = BusinessProfile.objects.get_or_create(business=business)
    initial = {"name": business.name, "industry": business.industry, "description": business.description, "phone": business.phone,
               "address": profile.address, "working_hours": profile.working_hours, "delivery_info": profile.delivery_info,
               "payment_info": profile.payment_info, "rules": profile.rules}
    form = SetupForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            for key in ("name", "industry", "description", "phone"):
                setattr(business, key, form.cleaned_data[key])
            business.save(update_fields=["name", "industry", "description", "phone"])
            for key in ("address", "working_hours", "delivery_info", "payment_info", "rules"):
                setattr(profile, key, form.cleaned_data[key])
            profile.save()
        return redirect("launch_catalog", business_id=business.pk)
    return render(request, "core/launch.html", {"screen": "setup", "business": business, "form": form})


@login_required
def catalog(request, business_id):
    business = owner_business(request, business_id)
    form = QuickItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        CatalogItem.objects.create(business=business, kind=form.cleaned_data["kind"], name=form.cleaned_data["name"],
                                   price=form.cleaned_data["price"], description=form.cleaned_data["description"], currency="KZT")
        return redirect("launch_catalog", business_id=business.pk)
    items = CatalogItem.objects.filter(business=business)
    return render(request, "core/launch.html", {"screen": "catalog", "business": business, "form": form, "items": items})


@login_required
@require_POST
def publish(request, business_id):
    business = owner_business(request, business_id)
    if not business.description.strip() or not CatalogItem.objects.filter(business=business, is_available=True).exists():
        messages.error(request, "Перед запуском заполните описание компании и добавьте хотя бы одну доступную позицию.")
        return redirect("launch_catalog", business_id=business.pk)
    business.public_chat_enabled = True
    business.save(update_fields=["public_chat_enabled"])
    return redirect("launch_ready", business_id=business.pk)


@login_required
def ready(request, business_id):
    business = owner_business(request, business_id)
    url = request.build_absolute_uri(reverse("public_chat_page", args=[business.slug]))
    return render(request, "core/launch.html", {"screen": "ready", "business": business, "public_url": url,
                                                 "item_count": CatalogItem.objects.filter(business=business).count(),
                                                 "enabled": business.public_chat_enabled})
