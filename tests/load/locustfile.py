from locust import HttpUser, task, between
import random
import string


class ShortenerUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        email = f"user{random.randint(1, 10000)}@example.com"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

        # Register
        self.client.post("/register", json={
            "email": email,
            "password": password
        })

        # Login and store token
        response = self.client.post("/token", data={
            "username": email,
            "password": password
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

        self.my_links = []
        for _ in range(3):
            response = self.client.post(
                "/links/shorten",
                json={"original_url": "https://example.com"},
                headers=self.headers
            )
            self.my_links.append(response.json()["short_code"])

    @task(5)
    def redirect_to_short_link(self):
        if self.my_links:
            short_code = random.choice(self.my_links)
            self.client.get(f"/{short_code}", name="/[short_code]")

    @task(2)
    def create_short_link(self):
        url = f"https://example.com/{''.join(random.choices(string.ascii_letters, k=10))}"
        self.client.post(
            "/links/shorten",
            json={"original_url": url},
            headers=self.headers
        )

    @task(1)
    def view_link_stats(self):
        if self.my_links:
            short_code = random.choice(self.my_links)
            self.client.get(
                f"/links/{short_code}/stats",
                headers=self.headers
            )

    @task(1)
    def view_user_links(self):
        self.client.get(
            "/users/me/links",
            headers=self.headers
        )

    @task(1)
    def delete_link(self):
        if self.my_links:
            short_code = self.my_links.pop(0)
            self.client.delete(
                f"/links/{short_code}",
                headers=self.headers
            )