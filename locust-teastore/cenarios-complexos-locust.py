import os
from locust import HttpUser, task, between
from bs4 import BeautifulSoup


# Configure host from environment for CI reproducibility
BASE_HOST = os.getenv("HOST", "http://localhost")
BASE_PORT = os.getenv("PORT", "8080")
BASE_PATH = os.getenv("BASE_PATH", "/tools.descartes.teastore.webui")


class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    host = f"{BASE_HOST}:{BASE_PORT}{BASE_PATH}"

    def on_start(self):
        self.login()

    def login(self):
        # GET LOGIN PAGE (aligned with JMeter/k6)
        with self.client.get("/login", name="GET /login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha GET /login_page")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                res.failure("CSRF não encontrado na tela de login")
                return

            token = csrf.get("value")

        # POST LOGIN ACTION CORRETO
        payload = {
            "username": "user2",
            "password": "password",
            "_csrf": token
        }

        with self.client.post("/loginAction", data=payload, name="POST /loginAction", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha no POST /login_action")
                return

    @task
    def fluxo(self):

        # HOME
        with self.client.get("/", name="GET /", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar home")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            cats = soup.select("a.menulink")

            if not cats:
                res.failure("Nenhuma categoria encontrada na home")
                return

            cat_link = cats[0].get("href")

        # CATEGORY
        with self.client.get(cat_link, name="GET /category", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar categoria")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            prods = soup.select("div.thumbnail a")

            if not prods:
                res.failure("Nenhum produto encontrado na categoria")
                return

            prod_link = prods[0].get("href")

        # PRODUCT PAGE
        with self.client.get(prod_link, name="GET /product", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar produto")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            pid_elem = soup.find("input", {"name": "productid"})
            pname_elem = soup.find("h2", {"class": "product-title"})

            if not pid_elem or not pname_elem:
                res.failure("Dados do produto não encontrados")
                return

            pid = pid_elem["value"]
            pname = pname_elem.text.strip()

        # GET CSRF FOR CART ACTION
        with self.client.get("/cart", name="GET /cart", catch_response=True) as res:
            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                res.failure("CSRF não encontrado no carrinho")
                return

            token = csrf["value"]

        # ADD TO CART
        payload = {
            "productid": pid,
            "quantity": "1",
            "addToCart": "Add to Cart",
            "_csrf": token
        }

        with self.client.post("/cartAction", data=payload, name="POST /add_to_cart", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao adicionar ao carrinho")
                return

        # VERIFY CART
        with self.client.get("/cart", name="GET /cart_final", catch_response=True) as res:
            if pname.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não apareceu no carrinho")
