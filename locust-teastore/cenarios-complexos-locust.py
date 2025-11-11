from locust import HttpUser, task, between, events
import logging
import requests
from bs4 import BeautifulSoup
import re

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("--- Resetando a base via API ---")
    host = environment.host.rstrip('/')
    try:
        res = requests.post(f"{host}/tools.descartes.teastore.webui/services/rest/persistence/reset", timeout=20)
        if res.status_code == 200:
            logging.info("Base OK")
        else:
            logging.warning(f"Reset retornou {res.status_code}")
    except Exception as e:
        logging.error(e)

class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    _csrf_token = None

    def extract_csrf(self, html):
        soup = BeautifulSoup(html, "html.parser")

        el = soup.select_one("input[name='_csrf']")
        if el and el.get("value"):
            return el["value"]

        el = soup.select_one("meta[name='_csrf']")
        if el and el.get("content"):
            return el["content"]

        m = re.search(r"_csrf['\"]?\s*[:=]\s*['\"]([^'\"]+)", html)
        if m:
            return m.group(1)

        return None

    def on_start(self):
        self.login()

    def login(self):
        with self.client.get("/tools.descartes.teastore.webui/login", name="/login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("login page falhou")
                return

            token = self.extract_csrf(res.text)
            if not token:
                res.failure("csrf login ausente")
                return

            self._csrf_token = token
            res.success()

        payload = {
            "username": "user1",
            "password": "password",
            "action": "login",
            "_csrf": self._csrf_token
        }

        with self.client.post("/tools.descartes.teastore.webui/loginAction", data=payload,
                              name="/login_action", catch_response=True, allow_redirects=True) as login_res:

            if login_res.status_code not in (200, 302):
                login_res.failure("status estranho")
                return

            token = self.extract_csrf(login_res.text)
            if token:
                self._csrf_token = token

            login_res.success()

    @task
    def browse_and_add_to_cart(self):
        with self.client.get("/tools.descartes.teastore.webui/", name="/", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("home falhou")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            link = soup.select_one("ul.nav-sidebar a.menulink") or soup.select_one("a.menulink")

            if not link or not link.get("href"):
                res.failure("categoria nao encontrada")
                return

            category = link["href"]

        with self.client.get(category, name="/categoria", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("categoria falhou")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            prod = soup.select_one("div.thumbnail a") or soup.select_one("a[href*='product']")

            if not prod or not prod.get("href"):
                res.failure("produto nao encontrado")
                return

            product = prod["href"]

        with self.client.get(product, name="/produto", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("produto falhou")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            name_el = soup.select_one("h2.product-title") or soup.select_one("h2.minipage-title")
            product_name = name_el.text.strip() if name_el else None

            id_el = soup.select_one("input[name='productid']")
            product_id = id_el.get("value") if id_el else None

            if not product_id:
                res.failure("id não encontrado")
                return

        cart_payload = {
            "productid": product_id,
            "addToCart": "Add to Cart",
            "_csrf": self._csrf_token
        }

        with self.client.post("/tools.descartes.teastore.webui/cartAction", data=cart_payload,
                              name="/add_cart", catch_response=True, allow_redirects=True) as add_res:
            if add_res.status_code not in (200, 302):
                add_res.failure("cartAction falhou")
                return
            add_res.success()

        with self.client.get("/tools.descartes.teastore.webui/cart", name="/cart", catch_response=True) as res:
            if product_name and product_name.lower().replace(" ", "") in res.text.lower().replace(" ", ""):
                res.success()
            else:
                res.failure("produto não está no carrinho")
