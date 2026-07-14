from locust import HttpUser, between, task


class KnowledgeRagUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        response = self.client.post("/api/login", json={"username": "admin", "password": "123456"})
        token = response.json().get("token", "")
        self.headers = {"Authorization": f"Bearer {token}"}

    @task(4)
    def health(self):
        self.client.get("/api/health")

    @task(1)
    def documents(self):
        self.client.get("/api/documents/list", headers=self.headers)