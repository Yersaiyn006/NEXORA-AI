"""Keep routine regression runs offline even when a developer .env has a live key."""
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class OfflineTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        self.offline = override_settings(NEXORA_AI_ENABLED=False)
        self.offline.enable()
        super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs):
        try:
            super().teardown_test_environment(**kwargs)
        finally:
            self.offline.disable()
