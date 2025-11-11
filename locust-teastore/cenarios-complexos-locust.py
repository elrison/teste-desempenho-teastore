# NOME DO ARQUIVO: locust-teastore/cenarios-complexos-locust.py

from locust import HttpUser, task, between, events
import logging
from bs4 import BeautifulSoup

# Prefixo padrão do TeaStore
BASE = "/tools.descartes.teastore.webui"

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("--- Resetando banco via API (Locust) ---")

    host = environment.host
    res = environment.runner.client.post(
        f"{host}{BASE}/services/rest/persistence/reset"
    )

    if res.status_code != 200:
        logging.error(f"Falha reset DB: HTTP {res.status_code}")
        environment.runner.quit()
    else:
        logging.info("--- Base resetada com sucesso ---")


class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    _csrf_token = None

    # -------------------------------
    # Helper para extrair CSRF
    # -------------------------------
    def extract_csrf(self, html_txt, msg):
        soup = BeautifulSoup(html_txt, "html.parser")

        for sel in [
            "input[name='_csrf']",
            "input[name=csrf]",
            "input[name=token]"
        ]:
            el = soup.select_one(sel)
            if el and el.get("value"):
                self._csrf_token = el["value"]
                return True

        logging.warning(msg)
        return False

    def on_start(self):
        self.login()

    # -------------------------------
    # LOGIN
    # -------------------------------
    def login(self):
        # GET login
        with self.client.get(f"{BASE}/login", name="/login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao carregar /login")
                return

            if not self.extract_csrf(res.text, "CSRF não encontrado no login"):
                res.failure("Falha no token CSRF do login")
                return

        # POST login
        data = {
            "username": "user1",
            "password": "password",
            "action": "login",
            "_csrf": self._csrf_token,
        }

        with self.client.post(
            f"{BASE}/loginAction",
            data=data,
            name="/loginAction",
            catch_response=True
        ) as res:

            if "Logout" not in res.text:
                res.failure("Login falhou (Logout não encontrado)")
                return

            self.extract_csrf(res.text, "CSRF pós login não encontrado")
            res.success()

    # -------------------------------
    # Cenário completo
    # -------------------------------
    @task
    def browse_and_add(self):

        # HOME
        with self.client.get(f"{BASE}/", name="/", catch_response=True) as res:
            self.extract_csrf(res.text, "CSRF home faltando")

            soup = BeautifulSoup(res.text, "html.parser")
            cat = soup.select_one("ul.nav-sidebar a.menulink")

            if not cat or not cat.get("href"):
                res.failure("Categoria não encontrada!")
                return

            # LINKS relativos → corrigidos
            category = BASE + cat["href"]
            res.success()

        # CATEGORIA
        with self.client.get(category, name="/category", catch_response=True) as res:
            self.extract_csrf(res.text, "CSRF categoria faltando")

            soup = BeautifulSoup(res.text, "html.parser")
            prod = soup.select_one("div.thumbnail a")

            if not prod or not prod.get("href"):
                res.failure("Produto não encontrado!")
                return

            product = BASE + prod["href"]
            res.success()

        # PRODUTO
        with self.client.get(product, name="/product", catch_response=True) as res:
            self.extract_csrf(res.text, "CSRF produto faltando")

            soup = BeautifulSoup(res.text, "html.parser")
            name_el = soup.select_one("h2.product-title") or soup.select_one("h2.minipage-title")
            id_el = soup.select_one("input[name='productid']")

            if not name_el or not id_el:
                res.failure("Informações do produto ausentes!")
                return

            name = name_el.text.strip()
            product_id = id_el.get("value").strip()
            res.success()

        # ADD CART
        payload = {
            "productid": product_id,
            "addToCart": "Add to Cart",
            "_csrf": self._csrf_token
        }

        with self.client.post(f"{BASE}/cartAction", data=payload, name="/add", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao adicionar ao carrinho")
                return

            self.extract_csrf(res.text, "CSRF cartAction faltando")
            res.success()

        # CART PAGE
        with self.client.get(f"{BASE}/cart", name="/cart", catch_response=True) as res:
            if name.lower().replace(" ", "") not in res.text.lower().replace(" ", ""):
                res.failure(f"Produto {name} não está no carrinho!")
            else:
                res.success()
