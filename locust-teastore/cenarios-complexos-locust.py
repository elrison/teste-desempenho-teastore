from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import requests, logging


@events.test_start.add_listener
def reset_database(environment, **kwargs):
    host = environment.host.rstrip('/')
    logging.info("🔄 Resetando base de dados...")
    try:
        r = requests.post(f"{host}/tools.descartes.teastore.webui/services/rest/persistence/reset")
        if r.status_code == 200:
            logging.info("✅ Base resetada com sucesso!")
        else:
            logging.warning(f"⚠️ Falha ao resetar: {r.status_code}")
    except Exception as e:
        logging.error(f"Erro ao resetar: {e}")


class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    base_url = "/tools.descartes.teastore.webui"

    def on_start(self):
        login_url = self.base_url + "/login"

        # GET login → capturar CSRF
        with self.client.get(login_url, name="/login", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha no GET /login")
                return

            soup = BeautifulSoup(r.text, "html.parser")
            csrf_input = soup.find("input", {"name": "_csrf"})

            if not csrf_input:
                r.failure("CSRF não encontrado no GET /login")
                return

            csrf_token = csrf_input.get("value")

        # POST login com CSRF
        payload = {
            "username": "user1",
            "password": "password",
            "_csrf": csrf_token,
            "signin": "Sign in",
            "referer": self.host + self.base_url + "/"
        }

        headers = {"Referer": self.host + login_url}

        with self.client.post(
            self.base_url + "/loginAction",
            data=payload,
            name="/loginAction",
            headers=headers,
            allow_redirects=True,
            catch_response=True
        ) as rp:

            # validar se o login realmente funcionou
            if rp.status_code != 200 or 'name="logout"' not in rp.text:
                rp.failure("Login falhou (CSRF ou credenciais)")
                return

            logging.info("✅ Login bem-sucedido!")

    @task
    def fluxo_completo(self):

        # HOME
        with self.client.get(self.base_url + "/", name="/home", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar Home")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            cats = soup.select("a.menulink")

            if not cats:
                res.failure("Nenhuma categoria encontrada (home vazia → login falhou antes)")
                return

            cat_link = cats[0].get("href")

        # CATEGORIA
        with self.client.get(cat_link, name="/categoria", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar categoria")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            prods = soup.select("div.thumbnail a")

            if not prods:
                res.failure("Nenhum produto encontrado")
                return

            prod_link = prods[0].get("href")

        # PRODUTO
        with self.client.get(prod_link, name="/produto", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar produto")
                return

            soup = BeautifulSoup(res.text, "html.parser")

            pid_elem = soup.select_one('input[name="productid"]')
            pname_elem = soup.select_one("h2.product-title")

            if not pid_elem or not pname_elem:
                res.failure("Produto sem dados")
                return

            pid = pid_elem.get("value")
            pname = pname_elem.text.strip()

        # ADD TO CART
        payload = {"productid": pid, "addToCart": "Add to Cart"}

        with self.client.post(
            self.base_url + "/cartAction",
            data=payload,
            name="/cartAction",
            catch_response=True
        ) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao adicionar ao carrinho")
                return

        # CART
        with self.client.get(self.base_url + "/cart", name="/cart", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar carrinho")
                return

            if pname.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não está no carrinho")
