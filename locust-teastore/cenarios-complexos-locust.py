# locust-teastore/cenarios-complexos-locust.py
from locust import HttpUser, task, between, events
import logging
import requests
from bs4 import BeautifulSoup

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("--- Preparando ambiente de teste: Resetando a base de dados via API ---")
    host = environment.host.rstrip('/')
    try:
        response = requests.post(f"{host}/tools.descartes.teastore.webui/services/rest/persistence/reset", timeout=30)
        if response.status_code == 200:
            logging.info("--- Base de dados resetada com sucesso ---")
        else:
            logging.error(f"--- FALHA AO RESETAR A BASE DE DADOS, status: {response.status_code} ---")
            environment.runner.quit()
    except requests.exceptions.RequestException as e:
        logging.error(f"--- FALHA CRÍTICA NO SETUP: {e} ---")
        environment.runner.quit()

class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    _csrf_token = None

    def on_start(self):
        self.login()

    def _extract_csrf(self, response_text, failure_message):
        soup = BeautifulSoup(response_text, "html.parser")
        token_element = soup.select_one("input[name='_csrf']")
        if not token_element or not token_element.has_attr("value"):
            logging.warning(failure_message)
            return False
        self._csrf_token = token_element["value"]
        return True

    def login(self):
        with self.client.get("/tools.descartes.teastore.webui/login", name="/login", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível carregar a página de login.")
                self.environment.runner.quit()
                return
            if not self._extract_csrf(response.text, "Não foi possível encontrar o _csrf token na página de login."):
                response.failure("Falha ao extrair _csrf token do login.")
                self.environment.runner.quit()
                return
            response.success()

        payload = {
            "username": "user1",
            "password": "password",
            "action": "login",
            "_csrf": self._csrf_token
        }
        with self.client.post("/tools.descartes.teastore.webui/loginAction", data=payload, name="/login_action", catch_response=True, allow_redirects=True) as login_response:
            # Accept 200 or 302
            if login_response.status_code not in (200, 302) or "Logout" not in login_response.text:
                logging.error(f"Falha no login. Token usado: {self._csrf_token}. Resposta (trecho): {login_response.text[:300]}")
                login_response.failure("Texto 'Logout' não encontrado após o login.")
                self.environment.runner.quit()
            else:
                login_response.success()
                self._extract_csrf(login_response.text, "Não foi possível extrair _csrf token da home pós-login.")

    @task
    def browse_and_add_to_cart(self):
        with self.client.get("/tools.descartes.teastore.webui/", name="/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a home.")
                return
            self._extract_csrf(response.text, "CSRF home faltando")
            soup = BeautifulSoup(response.text, "html.parser")
            category_link_element = soup.select_one("ul.nav-sidebar a.menulink")
            if not category_link_element or not category_link_element.has_attr("href"):
                response.failure("Não foi possível encontrar o link de categoria.")
                return
            category_link = category_link_element["href"]

        with self.client.get(category_link, name="/category", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a categoria.")
                return
            self._extract_csrf(response.text, "Não foi possível extrair _csrf token da categoria.")
            soup_cat = BeautifulSoup(response.text, "html.parser")
            product_link_element = soup_cat.select_one("div.thumbnail a")
            if not product_link_element or not product_link_element.has_attr("href"):
                response.failure("Não foi possível encontrar o link do produto.")
                return
            product_link = product_link_element["href"]

        with self.client.get(product_link, name="/product", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a página do produto.")
                return
            self._extract_csrf(response.text, "Não foi possível extrair _csrf token da página do produto.")
            soup_prod = BeautifulSoup(response.text, "html.parser")
            product_name_element = soup_prod.select_one("h2.product-title") or soup_prod.select_one("h2.minipage-title")
            if not product_name_element:
                response.failure("Não foi possível encontrar o nome do produto.")
                return
            product_name = product_name_element.text.strip()
            product_id_element = soup_prod.select_one("input[name='productid']")
            if not product_id_element or not product_id_element.has_attr("value"):
                response.failure("Não foi possível extrair o ID do produto.")
                return
            product_id = product_id_element["value"]

        cart_payload = {
            "productid": product_id,
            "addToCart": "Add to Cart",
            "_csrf": self._csrf_token
        }
        with self.client.post("/tools.descartes.teastore.webui/cartAction", data=cart_payload, name="/add_to_cart", catch_response=True, allow_redirects=True) as add_response:
            if add_response.status_code not in (200, 302):
                add_response.failure("Falha ao adicionar produto ao carrinho.")
                return
            self._extract_csrf(add_response.text, "CSRF after cartAction missing")

        with self.client.get("/tools.descartes.teastore.webui/cart", name="/cart_page", catch_response=True) as response:
            if product_name.lower().replace(" ", "") not in response.text.lower().replace(" ", ""):
                response.failure(f"Produto '{product_name}' não encontrado no carrinho.")
            else:
                response.success()
