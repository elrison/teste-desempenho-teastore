import os
from locust import HttpUser, task, between
from bs4 import BeautifulSoup


# Configure host from environment for CI reproducibility
BASE_HOST = os.getenv("HOST", "http://localhost")
BASE_PORT = os.getenv("PORT", "8080")
BASE_PATH = os.getenv("BASE_PATH", "/tools.descartes.teastore.webui")


class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)
    host = f"{BASE_HOST}:{BASE_PORT}{BASE_PATH}"

    def on_start(self):
        self.login()

    def login(self):
        # GET login page and extract CSRF
        with self.client.get("/login", name="GET /login", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha GET /login_page")
                self._dump_debug_page(res, "login_get")
                return

            token = self._extract_csrf(res.text)
            # If CSRF token is not present, proceed without it (some deployments don't use CSRF hidden input)
            if not token:
                # record debug page but don't abort the flow — we'll try login without token
                self._dump_debug_page(res, "login_get_no_csrf")

        # POST LOGIN ACTION
        payload = {
            "username": "user2",
            "password": "password",
        }
        if token:
            payload["_csrf"] = token

        with self.client.post("/loginAction", data=payload, name="POST /loginAction", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha no POST /login_action")
                self._dump_debug_page(res, "login_post_failure")
                return

        # try to update CSRF from the home page after login
        try:
            home = self.client.get("/", name="GET / after login")
            token = token or self._extract_csrf(home.text)
        except Exception:
            pass

    def _extract_csrf(self, body: str) -> str:
        """Robust CSRF extraction: input[name=_csrf], meta[name=_csrf], inline JS."""
        try:
            soup = BeautifulSoup(body, "html.parser")
            el = soup.find("input", {"name": "_csrf"})
            if el and el.get("value"):
                return el.get("value")

            meta = soup.find("meta", {"name": "_csrf"})
            if meta and meta.get("content"):
                return meta.get("content")

            import re
            m = re.search(r"_csrf['\"]?\s*[:=]\s*['\"]([^'\"]+)", body)
            if m:
                return m.group(1)
        except Exception:
            return None

        return None

    def _dump_debug_page(self, res, tag: str):
        """Save response HTML for debugging to logs/ with timestamp and tag."""
        try:
            os.makedirs("logs", exist_ok=True)
            import time, hashlib
            ts = int(time.time() * 1000)
            content = res.text if hasattr(res, 'text') else str(res)
            h = hashlib.sha1(content.encode("utf-8", errors="ignore")).hexdigest()[:8]
            fname = f"logs/locust_{tag}_{ts}_{h}.html"
            with open(fname, "w", encoding="utf-8", errors="ignore") as f:
                f.write(content)
        except Exception:
            pass

    @task
    def fluxo(self):

        # HOME
        with self.client.get("/", name="GET /", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar home")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            # try multiple selectors for category links
            cats = soup.select("a.menulink")
            if not cats:
                cats = soup.select("ul.nav-sidebar a")
            if not cats:
                cats = soup.select("a[href*='category']")

            if not cats:
                res.failure("Nenhuma categoria encontrada na home")
                self._dump_debug_page(res, "home_no_category")
                return

            cat_link = cats[0].get("href")
            # If the link contains the full base path (site uses absolute paths that include BASE_PATH),
            # convert it to a path relative to the configured host to avoid duplicating the base path.
            try:
                if cat_link.startswith(BASE_PATH):
                    # keep leading slash
                    cat_link = cat_link[len(BASE_PATH):] or '/'
            except Exception:
                pass

        # CATEGORY
        with self.client.get(cat_link, name="GET /category", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar categoria")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            # product selectors fallback
            prods = soup.select("div.thumbnail a")
            if not prods:
                prods = soup.select("a[href*='product']")
            if not prods:
                prods = soup.select("a.menulink")

            if not prods:
                res.failure("Nenhum produto encontrado na categoria")
                self._dump_debug_page(res, "category_no_product")
                return

            prod_link = prods[0].get("href")
            try:
                if prod_link.startswith(BASE_PATH):
                    prod_link = prod_link[len(BASE_PATH):] or '/'
            except Exception:
                pass

        # PRODUCT PAGE
        with self.client.get(prod_link, name="GET /product", catch_response=True) as res:
            if res.status_code != 200:
                res.failure("Falha ao acessar produto")
                return

            soup = BeautifulSoup(res.text, "html.parser")
            pid_elem = soup.find("input", {"name": "productid"})
            # some TeaStore versions use h2.minipage-title instead of h2.product-title
            pname_elem = soup.find("h2", {"class": "product-title"}) or soup.find("h2", {"class": "minipage-title"})

            if not pid_elem or not pname_elem:
                res.failure("Dados do produto não encontrados")
                self._dump_debug_page(res, "product_missing_data")
                return

            pid = pid_elem.get("value")
            pname = pname_elem.text.strip()

        # GET CSRF FOR CART ACTION
        with self.client.get("/cart", name="GET /cart", catch_response=True) as res:
            soup = BeautifulSoup(res.text, "html.parser")
            csrf = soup.find("input", {"name": "_csrf"})
            if not csrf:
                # cart may not require CSRF token in this deployment; proceed without it
                token = None
            else:
                token = csrf["value"]

        # ADD TO CART
        payload = {
            "productid": pid,
            "quantity": "1",
            "addToCart": "Add to Cart",
        }
        if token:
            payload["_csrf"] = token

        with self.client.post("/cartAction", data=payload, name="POST /add_to_cart", catch_response=True) as res:
            if res.status_code not in (200, 302):
                res.failure("Falha ao adicionar ao carrinho")
                return

        # VERIFY CART
        with self.client.get("/cart", name="GET /cart_final", catch_response=True) as res:
            if pname.lower() in res.text.lower():
                res.success()
            else:
                res.failure("Produto não apareceu no carrinho")

        # LOGOUT (TeaStore implements logout via POST to loginAction with logout param)
        with self.client.post("/loginAction", params={"logout": ""}, name="POST /logout", catch_response=True) as res:
            if res.status_code in (200, 302):
                res.success()
            else:
                res.failure("Falha ao deslogar")
