"""Business users must be able to sign back in without Django admin privileges."""
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from assistant_ai.rate_limits import consume


class BusinessLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if not consume([("login-ip", request.META.get("REMOTE_ADDR", "unknown"), 60, 10)]):
            response = HttpResponse("Слишком много попыток входа. Попробуйте через минуту.", status=429)
            response["Retry-After"] = "60"
            return response
        return super().post(request, *args, **kwargs)
