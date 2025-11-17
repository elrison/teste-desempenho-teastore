from locust import HttpUser, task, between, events
from bs4 import BeautifulSoup
import requests, logging

# 1. Função de reset MANTIDA.
# Ela é necessária para criar os usuários no banco de dados limpo.
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "/tools.descartes.teastore.webui"

    def on_start(self):
        login_url = self.base_url + "/login"
        
        with self.client.get(login_url, name="/login", catch_response=True) as response_get:
            if response_get.status_code != 200:
                response_get.failure(f"Falha no GET /login (HTTP {response_get.status_code})")
                return

        # --- INÍCIO DA CORREÇÃO (v23) ---
        # 2. Usuário corrigido para 'user1' (o padrão do TeaStore)
        referer_value = self.host + self.base_url + "/"
        
        payload = {
            "username": "user1", # <-- CORRIGIDO (voltando ao padrão)
            "password": "password",
            "signin": "Sign in",
            "referer": referer_value 
        }
        # --- FIM DA CORREÇÃO (v23) ---
        
        headers = {
            'Referer': self.host + login_url
        }
        
        with self.client.post(
            self.base_url + "/loginAction",
            data=payload, 
            name="/loginAction",
            headers=headers,
            allow_redirects=True,
            catch_response=True 
        ) as response_post:
        
            if response_post.status_code != 200 or 'name="logout"' not in response_post.text:
                logging.error(f">>> LOGIN FALHOU (v23). 'name=\"logout\"' NÃO ENCONTRADO. <<<")
                response_post.failure("Login falhou. 'Logout' não encontrado.")
                return
            
            logging.info("Login (v23) BEM-SUCEDIDO.")

    @task
    def fluxo_completo(self):
        # Home Page (agora deve estar logado)
        with self.client.get(self.base_url + "/", name="/home", catch_response=True) as res:
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
        with self.client.get(cat_link, name="/categoria", catch_response=True) as res:
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
        with self.client.get(prod_link, name="/produto", catch_response=True) as res:
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
        with self.client.post(
            self.base_url + "/cartAction",
            data=payload, 
            name="/cartAction",
            catch_response=True
        ) as res:
            if res.status_code not in (200, 302):
                res.failure(f"Falha ao adicionar ao carrinho (HTTP {res.status_code})")
                return

        # Cart Page
        with self.client.get(self.base_url + "/cart", name="/cart", catch_response=True) as res:
            if res.status_code != 200:
                res.failure(f"Falha ao acessar Carrinho (HTTP {res.status_code})")
                return
            
            # Validação final
            if pname.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não encontrado no carrinho")