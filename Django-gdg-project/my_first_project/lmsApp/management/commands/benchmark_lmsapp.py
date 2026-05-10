import statistics
import time

from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import override_settings


class Command(BaseCommand):
    help = "Benchmark a small set of LMS HTTP endpoints."

    def add_arguments(self, parser):
        parser.add_argument(
            "--iterations",
            type=int,
            default=5,
            help="Number of requests to average per endpoint.",
        )

    def handle(self, *args, **options):
        iterations = max(1, options["iterations"])
        client = Client()
        endpoints = [
            ("home", "/"),
            ("book_list", "/books/"),
            ("author_list", "/authors/"),
        ]

        self.stdout.write(f"Running {iterations} iterations per endpoint...")

        with override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"]):
            for label, path in endpoints:
                durations = []
                status_code = None
                for _ in range(iterations):
                    start = time.perf_counter()
                    response = client.get(path)
                    durations.append((time.perf_counter() - start) * 1000)
                    status_code = response.status_code

                self.stdout.write(
                    f"{label}: status={status_code} avg={statistics.mean(durations):.2f}ms "
                    f"min={min(durations):.2f}ms max={max(durations):.2f}ms"
                )
