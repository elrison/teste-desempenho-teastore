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

    # --- INÍCIO DA CORREÇÃO (v10) ---
    # A função extract_csrf foi removida pois o login não usa CSRF.

    def on_start(self):
        # Login GET (Opcional, mas bom para simular o 1º acesso)
        self.client.get(
            "/tools.descartes.teastore.webui/login",
            name="/login"
        )
            
        # Login POST (Payload agora sem CSRF)
        payload = {"username": "user1", "password": "password"}
        res = self.client.post(
            "/tools.descartes.teastore.webui/loginAction",
            data=payload, name="/loginAction",
            allow_redirects=True
        )
        
        # O 'allow_redirects=True' já cuida da checagem de sucesso
        if res.status_code not in (200, 302):
             res.failure(f"Falha no loginAction (HTTP {res.status_code})")
    # --- FIM DA CORREÇÃO (v10) ---

    @task
    def fluxo_completo(self):
        # Home Page
        res = self.client.get(
            "/tools.descartes.teastore.webui/", name="/home"
        )
        if res.status_code != 200:
            res.failure(f"Falha ao acessar Home (HTTP {res.status_code})")
            return
        soup = BeautifulSoup(res.text, "html.parser")
        
        cats = soup.select("a.menulink")
        if not cats:
            res.failure("Categoria não encontrada")
            return
        cat_link = cats[0].get("href") # Pega o primeiro

        # Categoria Page
        res = self.client.get(
            cat_link, name="/categoria"
        )
        if res.status_code != 200:
            res.failure(f"Falha ao acessar Categoria (HTTP {res.status_code})")
            return
        soup = BeautifulSoup(res.text, "html.parser")
        
        prods = soup.select("div.thumbnail a")
        if not prods:
            res.failure("Produto não encontrado")
            return
        prod_link = prods[0].get("href") # Pega o primeiro

        # Produto Page
        res = self.client.get(
            prod_link, name="/produto"
        )
        if res.status_code != 200:
            res.failure(f"Falha ao acessar Produto (HTTP {res.status_code})")
            return
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        pid_elem = soup.select_one('input[name="productid"]')
        pname_elem = soup.select_one("h2.product-title")
        
        if not pid_elem or not pname_elem:
            res.failure("Detalhes do produto ausentes")
            return
        
        pid = pid_elem.get("value")
        pname = pname_elem.text.strip()

        # Add to cart (já estava correto, sem CSRF)
        payload = {"productid": pid, "addToCart": "Add to Cart"}
        res = self.client.post(
            "/tools.descartes.teastore.webui/cartAction",
            data=payload, name="/cartAction"
        )
        
        if res.status_code not in (200, 302):
            res.failure(f"Falha ao adicionar ao carrinho (HTTP {res.status_code})")
            return

        # Cart Page
        res = self.client.get(
            "/tools.descartes.teastore.webui/cart", name="/cart"
        )
        if res.status_code != 200:
            res.failure(f"Falha ao acessar Carrinho (HTTP {res.status_code})")
            return
        
        # Validação final
        if pname.lower() in res.text.lower():
            res.success()
        else:
            res.failure("Produto não encontrado no carrinho")