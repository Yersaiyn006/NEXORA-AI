
from django import forms
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from assistant_ai.rate_limits import consume
from core.models import Business, Membership


User = get_user_model()


class BusinessRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        max_length=254,
    )

    company_name = forms.CharField(
        label="Название компании",
        max_length=150,
    )

    industry = forms.CharField(
        label="Сфера деятельности",
        max_length=100,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "company_name",
            "industry",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Этот email уже зарегистрирован."
            )

        return email


@require_http_methods(["GET", "POST"])
def register_business(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = BusinessRegistrationForm(request.POST or None)

    if request.method == "POST":
        ip = request.META.get("REMOTE_ADDR", "unknown")

        if not consume([
            ("registration-ip", ip, 3600, 5)
        ]):
            response = HttpResponse(
                "Слишком много попыток регистрации. "
                "Попробуйте позже.",
                status=429,
            )
            response["Retry-After"] = "3600"
            return response

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.email = form.cleaned_data["email"]
                    user.save()

                    business = Business.objects.create(
                        name=form.cleaned_data["company_name"],
                        industry=form.cleaned_data["industry"],
                        public_chat_enabled=False,
                    )

                    Membership.objects.create(
                        user=user,
                        business=business,
                        role="owner",
                    )

            except IntegrityError:
                form.add_error(
                    None,
                    "Не удалось завершить регистрацию. "
                    "Попробуйте ещё раз.",
                )

            else:
                login(
                    request,
                    user,
                    backend=(
                        "django.contrib.auth.backends."
                        "ModelBackend"
                    ),
                )

                return redirect(
                    "launch_setup",
                    business_id=business.pk,
                )

    return render(
        request,
        "core/register.html",
        {"form": form},
    )
