from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import requests, logging

@events.test_start.add_listener
def reset_database(environment, **kwargs):
    host = environment.host.rstrip("/")
    reset_url = f"{host}/tools.descartes.teastore.persistence/services/rest/persistence/reset"

    logging.info(f"🔄 Resetando base em {reset_url} ...")

    try:
        r = requests.post(reset_url)
        if r.status_code == 200:
            logging.info("✅ Base resetada com sucesso")
        else:
            logging.warning(f"⚠️ Falha ao resetar: {r.status_code}")
    except Exception as e:
        logging.error(e)


class TeaStoreUser(HttpUser):

    wait_time = between(1, 2)
    base_url = ""   # <-- ESSA É A CORREÇÃO CRÍTICA

    def on_start(self):

        # GET LOGIN
        with self.client.get("/login", name="/login", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha GET /login")
                return
            
            soup = BeautifulSoup(r.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})

            if not csrf:
                r.failure("CSRF não encontrado no login")
                return

            csrf_token = csrf["value"]

        # POST LOGIN
        payload = {
            "username": "user1",
            "password": "password",
            "_csrf": csrf_token,
            "signin": "Sign in",
            "referer": self.host + "/home"
        }

        with self.client.post(
            "/loginAction",
            data=payload,
            name="/loginAction",
            allow_redirects=True,
            catch_response=True
        ) as rp:
            if rp.status_code != 200 or "logout" not in rp.text.lower():
                rp.failure("Login falhou")
                return

            logging.info("✅ Login bem-sucedido!")


    @task
    def fluxo_completo(self):

        # HOME CORRETO
        with self.client.get("/home", name="/home", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha ao acessar /home")
                return

            soup = BeautifulSoup(r.text, "html.parser")
            cats = soup.select("a.menulink")

            if not cats:
                r.failure("Nenhuma categoria encontrada")
                return

            cat = cats[0]["href"]

        # Categoria
        with self.client.get(cat, name="/categoria", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha categoria")
                return

            soup = BeautifulSoup(r.text, "html.parser")
            prods = soup.select("div.thumbnail a")

            if not prods:
                r.failure("Nenhum produto encontrado")
                return

            prod = prods[0]["href"]

        # Produto
        with self.client.get(prod, name="/produto", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha produto")
                return

            soup = BeautifulSoup(r.text, "html.parser")
            pid_elem = soup.select_one('input[name="productid"]')
            pname_elem = soup.select_one("h2.product-title")

            if not pid_elem or not pname_elem:
                r.failure("Produto sem dados")
                return

            pid = pid_elem["value"]
            pname = pname_elem.text.strip()

        # Add to cart
        with self.client.post(
            "/cartAction",
            data={"productid": pid, "addToCart": "Add to Cart"},
            name="/cartAction",
            catch_response=True
        ) as r:
            if r.status_code not in (200, 302):
                r.failure("Falha ao adicionar ao carrinho")
                return

        # Cart
        with self.client.get("/cart", name="/cart", catch_response=True) as r:
            if r.status_code != 200:
                r.failure("Falha carrinho")
                return

            if pname.lower() in r.text.lower():
                r.success()
            else:
                r.failure("Produto não está no carrinho")
