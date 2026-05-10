from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from getpass import getpass


class Command(BaseCommand):
    help = "Create or update staff/admin users interactively."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Role user setup"))
        self._create_or_update("staff", is_staff=True, is_superuser=False)
        self._create_or_update("admin", is_staff=True, is_superuser=True)

    def _create_or_update(self, role, is_staff, is_superuser):
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE(f"{role.title()} account"))
        username = input(f"Username for {role} (leave blank to skip): ").strip()
        if not username:
            self.stdout.write(self.style.WARNING(f"Skipped {role}."))
            return

        email = input("Email (optional): ").strip()

        password = getpass("Password (leave blank to keep existing): ")
        password_confirm = getpass("Confirm password: ") if password else ""
        if password and password != password_confirm:
            self.stdout.write(self.style.ERROR("Passwords do not match. Skipping."))
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username)
        user.role = role
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        if email:
            user.email = email
        if password:
            user.set_password(password)
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} {role} user: {username}"))
