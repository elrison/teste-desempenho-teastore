from locust import HttpUser, task, between, events
import logging
import requests
from bs4 import BeautifulSoup

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logging.info("--- Preparando ambiente de teste: Resetando a base de dados via API ---")
    host = environment.host
    try:
        response = requests.post(f"{host}/tools.descartes.teastore.webui/services/rest/persistence/reset")
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

    def on_start(self):
        self.login()

    def login(self):
        # 1. GET na página de login (importante para cookies/session)
        with self.client.get("/tools.descartes.teastore.webui/login", name="/login_page", catch_response=True) as response:
            if response.status_code != 200 or "Login" not in response.text:
                response.failure("Não foi possível carregar a página de login.")
                self.environment.runner.quit()
                return

        # 2. POST para autenticar
        payload = {
            "username": "user1",
            "password": "password",
            "action": "login"
        }
        with self.client.post(
            "/tools.descartes.teastore.webui/loginAction",
            data=payload,
            name="/login_action",
            catch_response=True
        ) as login_response:
            if login_response.status_code != 200 or "Logout" not in login_response.text:
                login_response.failure("Texto 'Logout' não encontrado após o login.")
                self.environment.runner.quit()
            else:
                login_response.success()

    @task
    def browse_and_add_to_cart(self):
        # 1. Página inicial
        with self.client.get("/tools.descartes.teastore.webui/", name="/", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a home.")
                return
            soup = BeautifulSoup(response.text, "html.parser")
            category_link_element = soup.select_one("ul.nav-sidebar a.menulink")
            if not category_link_element or not category_link_element.has_attr("href"):
                response.failure("Não foi possível encontrar o link de categoria.")
                return
            category_link = category_link_element["href"]

        # 2. Página de categoria
        with self.client.get(category_link, name="/category", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a categoria.")
                return
            soup = BeautifulSoup(response.text, "html.parser")
            product_link_element = soup.select_one("div.thumbnail a")
            if not product_link_element or not product_link_element.has_attr("href"):
                response.failure("Não foi possível encontrar o link do produto.")
                return
            product_link = product_link_element["href"]

        # 3. Página do produto
        with self.client.get(product_link, name="/product", catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Não foi possível acessar a página do produto.")
                return
            soup = BeautifulSoup(response.text, "html.parser")
            # Nome do produto (tenta por .product-title, depois .minipage-title)
            product_name_element = soup.select_one("h2.product-title") or soup.select_one("h2.minipage-title")
            if not product_name_element:
                response.failure("Não foi possível encontrar o nome do produto.")
                return
            product_name = product_name_element.text.strip()
            # ID do produto
            product_id_element = soup.select_one("input[name='productid']")
            if not product_id_element or not product_id_element.has_attr("value"):
                response.failure("Não foi possível extrair o ID do produto.")
                return
            product_id = product_id_element["value"]

        # 4. Adiciona ao carrinho (payload igual ao HTML do form)
        cart_payload = {
            "productid": product_id,
            "addToCart": "Add to Cart"
        }
        with self.client.post(
            "/tools.descartes.teastore.webui/cartAction",
            data=cart_payload,
            name="/add_to_cart",
            catch_response=True
        ) as add_response:
            if add_response.status_code != 200:
                add_response.failure("Falha ao adicionar produto ao carrinho.")
                return

        # 5. Verifica se o produto está no carrinho (CHECAGEM CORRIGIDA)
        with self.client.get("/tools.descartes.teastore.webui/cart", name="/cart_page", catch_response=True) as response:
            # DEBUG: Imprime o HTML do carrinho para analisar como o produto aparece
            # print("\n\n==== HTML do carrinho ====\n")
            # print(response.text)
            # print("\n==== FIM HTML do carrinho ====\n\n")
            # Checagem menos rígida: ignora maiúsculas/minúsculas e espaços extras
            if product_name.lower().replace(" ", "") not in response.text.lower().replace(" ", ""):
                response.failure(f"Produto '{product_name}' não encontrado no carrinho.")
            else:
                response.success()