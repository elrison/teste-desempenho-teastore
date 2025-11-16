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

    def on_start(self):
        # --- INÍCIO DA CORREÇÃO (v14) ---
        # 1. FAZ O GET NA PÁGINA DE LOGIN
        res_get = self.client.get(
            "/tools.descartes.teastore.webui/login",
            name="/login"
        )
        if res_get.status_code != 200:
             res_get.failure(f"Falha no GET /login (HTTP {res_get.status_code})")
             return

        # 2. FAZ O POST DO LOGIN
        payload = {
            "username": "user1",
            "password": "password",
            "signin": "Sign in"
        }
        
        res_post = self.client.post(
            "/tools.descartes.teastore.webui/loginAction",
            data=payload, 
            name="/loginAction",
            allow_redirects=True # Queremos o HTML da página /home
        )
        
        # 3. VALIDAÇÃO EXPLÍCITA
        if res_post.status_code != 200:
            res_post.failure(f"Falha no POST /loginAction (HTTP {res_post.status_code})")
            return
            
        # A página de resposta DEVE conter "Logout" se o login funcionou
        if 'name="logout"' not in res_post.text:
            logging.error(">>> LOGIN FALHOU. 'name=\"logout\"' NÃO ENCONTRADO NA RESPOSTA. <<<")
            res_post.failure("Login falhou. 'Logout' não encontrado.")
            return # Para o usuário
        
        logging.info("Login (v14) BEM-SUCEDIDO.")
    # --- FIM DA CORREÇÃO (v14) ---

    @task
    def fluxo_completo(self):
        # Home Page (agora deve estar logado)
        res = self.client.get(
            "/tools.descartes.teastore.webui/", name="/home"
        )
        if res.status_code != 200:
            res.failure(f"Falha ao acessar Home (HTTP {res.status_code})")
            return
        soup = BeautifulSoup(res.text, "html.parser")
        
        cats = soup.select("a.menulink")
        if not cats:
            res.failure("Categoria não encontrada (usuário logado)")
            return
        cat_link = cats[0].get("href")

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
        prod_link = prods[0].get("href")

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

        # Add to cart
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