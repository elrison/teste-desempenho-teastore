import os
from locust import HttpUser, task, between


BASE_HOST = os.getenv("HOST", "http://localhost")
BASE_PORT = os.getenv("PORT", "8080")
BASE_PATH = os.getenv("BASE_PATH", "/tools.descartes.teastore.webui")


class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    host = f"{BASE_HOST}:{BASE_PORT}{BASE_PATH}"

    @task
    def test_flow(self):
        # Login
        with self.client.get("/login", name="GET /login", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"GET /login falhou: {response.status_code}")

        with self.client.post("/loginAction", name="POST /loginAction", data={
            "username": "user1",
            "password": "password",
        }, catch_response=True) as login_resp:
            if login_resp.status_code in (200, 302):
                login_resp.success()
            else:
                login_resp.failure(f"Login falhou: {login_resp.status_code}")

        # Home
        with self.client.get("/", name="GET /", catch_response=True) as home_resp:
            if home_resp.status_code == 200:
                home_resp.success()
            else:
                home_resp.failure(f"GET / falhou: {home_resp.status_code}")

        # Categoria
        with self.client.get("/category", name="GET /category", catch_response=True) as cat_resp:
            if cat_resp.status_code == 200:
                cat_resp.success()
            else:
                cat_resp.failure(f"GET /category falhou: {cat_resp.status_code}")

        # Produto
        with self.client.get("/product", name="GET /product", catch_response=True) as prod_resp:
            if prod_resp.status_code == 200:
                prod_resp.success()
            else:
                prod_resp.failure(f"GET /produto falhou: {prod_resp.status_code}")

        # Logout
        with self.client.post("/loginAction?logout=", name="POST /logout", catch_response=True) as logout_resp:
            if logout_resp.status_code in (200, 302):
                logout_resp.success()
            else:
                logout_resp.failure(f"Logout falhou: {logout_resp.status_code}")
