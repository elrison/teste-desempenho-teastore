from locust import HttpUser, task, between
from bs4 import BeautifulSoup

class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    base = "/tools.descartes.teastore.webui"

    def on_start(self):
        self.login()

    def login(self):
        # 1. GET LOGIN PAGE
        with self.client.get(self.base + "/login", name="/login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha GET /login")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                res.failure("CSRF não encontrado")
                return

            token = csrf.get("value")

        # 2. POST LOGIN
        payload = {
            "username": "user2",
            "password": "password",
            "_csrf": token
        }

        with self.client.post(
            self.base + "/login",
            data=payload,
            name="/loginAction",
            catch_response=True
        ) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha no login (POST)")
            else:
                res.success()

    @task
    def fluxo_completo(self):

        # HOME
        with self.client.get(self.base + "/", name="/home", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar /home")
                return
            
            soup = BeautifulSoup(res.text, "html.parser")
            cats = soup.select("a.menulink")
            if not cats:
                res.failure("Nenhuma categoria encontrada")
                return
            cat_link = cats[0]["href"]

        # CATEGORY
        with self.client.get(cat_link, name="/categoria", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha categoria")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            prods = soup.select("div.thumbnail a")
            if not prods:
                res.failure("Nenhum produto encontrado na categoria")
                return
            prod_link = prods[0]["href"]

        # PRODUCT
        with self.client.get(prod_link, name="/produto", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha produto")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            pid = soup.find("input", {"name": "productid"})
            pname = soup.find("h2", {"class": "product-title"})
            if not pid or not pname:
                res.failure("Informações do produto ausentes")
                return

            pid_value = pid["value"]
            pname_text = pname.text.strip()

        # GET CSRF FOR ADD TO CART
        with self.client.get(self.base + "/cart", name="/cart_load", catch_response=True) as res:
            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                res.failure("CSRF para cartAction não encontrado")
                return
            token = csrf["value"]

        # ADD TO CART
        payload = {
            "productid": pid_value,
            "quantity": "1",
            "addToCart": "Add to Cart",
            "_csrf": token
        }

        with self.client.post(
            self.base + "/cartAction",
            name="/cartAction",
            data=payload,
            catch_response=True
        ) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao adicionar ao carrinho")
                return

        # VERIFY CART
        with self.client.get(self.base + "/cart", name="/cart", catch_response=True) as res:
            if pname_text.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não apareceu no carrinho")
