from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Author, Book, Category, Member


User = get_user_model()


class LMSEndToEndTests(StaticLiveServerTestCase):
	@classmethod
	def setUpTestData(cls):
		cls.staff_user = User.objects.create_user(
			username="staff_user",
			password="staff_pass123",
			role="staff",
		)
		cls.admin_user = User.objects.create_user(
			username="admin_user",
			password="admin_pass123",
			role="admin",
		)
		cls.member_user = User.objects.create_user(
			username="member_user",
			password="member_pass123",
			role="member",
		)
		cls.member = Member.objects.create(
			member_name="Test Member",
			email="member@example.com",
			department="CS",
			dorm="Block-A",
			user=cls.member_user,
		)
		cls.author = Author.objects.create(
			author_name="Test Author",
			author_email="author@example.com",
		)
		cls.category = Category.objects.create(category_name="Fiction")
		cls.book = Book.objects.create(
			ISBN="ISBN-12345",
			title="Sample Book",
			total_copies=3,
			publication_date=timezone.now().date(),
			max_loan_duration=7,
			author=cls.author,
		)
		cls.book.category.add(cls.category)

	def setUp(self):
		self.api_client = APIClient()
		author, _ = Author.objects.get_or_create(
			author_name="Test Author",
			defaults={"author_email": "author@example.com"},
		)
		category, _ = Category.objects.get_or_create(category_name="Fiction")
		self.book, _ = Book.objects.get_or_create(
			ISBN="ISBN-12345",
			defaults={
				"title": "Sample Book",
				"total_copies": 3,
				"publication_date": timezone.now().date(),
				"max_loan_duration": 7,
				"author": author,
			},
		)
		if self.book.author_id != author.author_id:
			self.book.author = author
			self.book.save(update_fields=["author"])
		self.book.category.add(category)
		self.staff_user, _ = User.objects.get_or_create(
			username="staff_user",
			defaults={"role": "staff"},
		)
		if not self.staff_user.has_usable_password():
			self.staff_user.set_password("staff_pass123")
			self.staff_user.save(update_fields=["password"])
		self.admin_user, _ = User.objects.get_or_create(
			username="admin_user",
			defaults={"role": "admin"},
		)
		if not self.admin_user.has_usable_password():
			self.admin_user.set_password("admin_pass123")
			self.admin_user.save(update_fields=["password"])
		self.member_user, _ = User.objects.get_or_create(
			username="member_user",
			defaults={"role": "member"},
		)
		if not self.member_user.has_usable_password():
			self.member_user.set_password("member_pass123")
			self.member_user.save(update_fields=["password"])
		Member.objects.get_or_create(
			user=self.member_user,
			defaults={
				"member_name": "Test Member",
				"email": "member@example.com",
				"department": "CS",
				"dorm": "Block-A",
			},
		)
		author, _ = Author.objects.get_or_create(
			author_name="Test Author",
			defaults={"author_email": "author@example.com"},
		)
		category, _ = Category.objects.get_or_create(category_name="Fiction")
		book, _ = Book.objects.get_or_create(
			ISBN="ISBN-12345",
			defaults={
				"title": "Sample Book",
				"total_copies": 3,
				"publication_date": timezone.now().date(),
				"max_loan_duration": 7,
				"author": author,
			},
		)
		book.category.add(category)

	def test_home_page_loads(self):
		response = self.client.get(reverse("home-role"))
		self.assertEqual(response.status_code, 200)

	def test_member_register_and_login(self):
		User.objects.filter(username="new_member_e2e").delete()
		register_payload = {
			"member_name": "New Member",
			"email": "new_member@example.com",
			"department": "CS",
			"dorm": "Block-A",
			"username": "new_member_e2e",
			"password": "secure_pass123",
			"password_confirm": "secure_pass123",
		}
		response = self.client.post(reverse("register"), register_payload, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(User.objects.filter(username="new_member_e2e").exists())

		login_payload = {"username": "member_user", "password": "member_pass123"}
		response = self.client.post(reverse("login"), login_payload, follow=True)
		self.assertEqual(response.status_code, 200)
		self.assertIn("_auth_user_id", self.client.session)

	def test_role_dashboards_require_login(self):
		response = self.client.get(reverse("staff_dashboard"))
		self.assertEqual(response.status_code, 302)
		response = self.client.get(reverse("admin_dashboard"))
		self.assertEqual(response.status_code, 302)

	def test_staff_login_page_loads(self):
		response = self.client.get(reverse("login_staff"))
		self.assertEqual(response.status_code, 200)

	def test_staff_login_dashboard(self):
		self.client.force_login(self.staff_user)
		dashboard_response = self.client.get(reverse("staff_dashboard"))
		self.assertEqual(dashboard_response.status_code, 200)

	def test_staff_login_with_is_staff_flag(self):
		User.objects.filter(username="staff_flag_user").delete()
		staff_flag_user = User.objects.create_user(
			username="staff_flag_user",
			password="staff_flag_pass123",
			role="member",
			is_staff=True,
		)
		login_payload = {
			"username": "staff_flag_user",
			"password": "staff_flag_pass123",
		}
		response = self.client.post(reverse("login_staff"), login_payload, follow=True)
		self.assertEqual(response.status_code, 200)
		dashboard_response = self.client.get(reverse("staff_dashboard"))
		self.assertEqual(dashboard_response.status_code, 200)

	def test_staff_and_admin_can_view_book_list(self):
		self.client.force_login(self.staff_user)
		staff_response = self.client.get(reverse("book_list"))
		self.assertEqual(staff_response.status_code, 200)
		self.assertContains(staff_response, "Edit")
		self.assertContains(staff_response, "Delete")
		self.client.logout()

		self.client.force_login(self.admin_user)
		admin_response = self.client.get(reverse("book_list"))
		self.assertEqual(admin_response.status_code, 200)
		self.assertContains(admin_response, "Edit")
		self.assertContains(admin_response, "Delete")

	def test_member_cannot_see_edit_delete_buttons(self):
		self.client.force_login(self.member_user)
		response = self.client.get(reverse("book_list"))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Edit")
		self.assertNotContains(response, "Delete")

	def test_member_cannot_see_edit_delete_on_detail(self):
		self.client.force_login(self.member_user)
		response = self.client.get(reverse("book_detail", args=[self.book.book_id]))
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, "Edit")
		self.assertNotContains(response, "Delete")

	def test_api_health_and_login(self):
		health_response = self.api_client.get(f"{self.live_server_url}/api/v1/health/")
		self.assertEqual(health_response.status_code, 200)
		self.assertEqual(health_response.data.get("status"), "ok")

		register_payload = {
			"username": "api_user",
			"email": "api_user@example.com",
			"password": "api_pass123",
			"role": "member",
		}
		register_response = self.api_client.post(
			f"{self.live_server_url}/api/v1/auth/register/",
			register_payload,
			format="json",
		)
		self.assertEqual(register_response.status_code, 201)

		login_response = self.api_client.post(
			f"{self.live_server_url}/api/v1/auth/login/",
			{"username": "api_user", "password": "api_pass123"},
			format="json",
		)
		self.assertEqual(login_response.status_code, 200)
		token = login_response.data["tokens"]["access"]

		self.api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
		authors_response = self.api_client.get(f"{self.live_server_url}/api/v1/authors/")
		self.assertEqual(authors_response.status_code, 200)

		members_response = self.api_client.get(f"{self.live_server_url}/api/v1/members/")
		self.assertEqual(members_response.status_code, 200)
