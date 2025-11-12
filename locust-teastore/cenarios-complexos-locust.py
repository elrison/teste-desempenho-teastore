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

    def extract_csrf(self, html):
        soup = BeautifulSoup(html, "html.parser")
        token = soup.select_one('input[name="_csrf"]') or soup.select_one('meta[name="_csrf"]')
        return token.get("value") or token.get("content") if token else None

    def on_start(self):
        res = self.client.get("/tools.descartes.teastore.webui/login", name="/login")
        if res.status_code != 200:
            res.failure("Falha ao abrir login")
            return
        csrf = self.extract_csrf(res.text)
        if not csrf:
            res.failure("CSRF ausente no login")
            return
        payload = {"username": "user1", "password": "password", "_csrf": csrf}
        res = self.client.post("/tools.descartes.teastore.webui/loginAction", data=payload, name="/loginAction", allow_redirects=True)
        if res.status_code not in (200, 302):
            res.failure("Falha no loginAction")

    @task
    def fluxo_completo(self):
        # Home
        res = self.client.get("/tools.descartes.teastore.webui/", name="/home")
        soup = BeautifulSoup(res.text, "html.parser")
        cat = soup.select_one("a.menulink")
        if not cat:
            res.failure("Categoria não encontrada")
            return

        # Categoria
        res = self.client.get(cat["href"], name="/categoria")
        soup = BeautifulSoup(res.text, "html.parser")
        prod = soup.select_one("div.thumbnail a")
        if not prod:
            res.failure("Produto não encontrado")
            return

        # Produto
        res = self.client.get(prod["href"], name="/produto")
        soup = BeautifulSoup(res.text, "html.parser")
        csrf = self.extract_csrf(res.text)
        pid = soup.select_one('input[name="productid"]').get("value")
        pname = soup.select_one("h2.product-title").text.strip()

        # Add to cart
        payload = {"productid": pid, "addToCart": "Add to Cart", "_csrf": csrf}
        self.client.post("/tools.descartes.teastore.webui/cartAction", data=payload, name="/cartAction")

        # Cart
        cart = self.client.get("/tools.descartes.teastore.webui/cart", name="/cart")
        if pname.lower() in cart.text.lower():
            cart.success()
        else:
            cart.failure("Produto não encontrado no carrinho")
