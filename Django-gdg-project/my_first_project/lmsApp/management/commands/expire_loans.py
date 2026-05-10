from django.core.management.base import BaseCommand
from lmsApp.utils import expire_loans

class Command(BaseCommand):
    help = "Automatically expire loans past pickup deadline"

    def handle(self, *args, **kwargs):
        expire_loans()
        self.stdout.write(self.style.SUCCESS("Expired loans processed."))
