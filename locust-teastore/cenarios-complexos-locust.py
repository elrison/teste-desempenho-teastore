from locust import HttpUser, task, between
from bs4 import BeautifulSoup

class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    host = "http://localhost:8080/tools.descartes.teastore.webui"

    def on_start(self):
        self.login()

    def login(self):
        # GET LOGIN PAGE
        with self.client.get("/login", name="GET /login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha GET /login")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                res.failure("CSRF não encontrado na tela de login")
                return

            token = csrf.get("value")

        # POST LOGIN
        payload = {
            "username": "user2",
            "password": "password",
            "_csrf": token
        }

        with self.client.post("/login", data=payload, name="POST /login", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao fazer login (POST)")
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
        with self.client.get(cat_link, name="GET categoria", catch_response=True) as res:
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
        with self.client.get(prod_link, name="GET produto", catch_response=True) as res:
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
        with self.client.get("/cart", name="GET /cart para csrf", catch_response=True) as res:
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

        with self.client.post("/cartAction", data=payload, name="POST /cartAction", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao adicionar ao carrinho")
                return

        # VERIFY CART
        with self.client.get("/cart", name="GET /cart final", catch_response=True) as res:
            if pname.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não apareceu no carrinho")
