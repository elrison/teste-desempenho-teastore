import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

const BASE_URL = "http://localhost:18081/tools.descartes.teastore.webui";
const DOMAIN_URL = "http://localhost:18081";

export const options = {
  vus: 10,
  duration: "30s",
};

export function setup() {
  let res = http.post(`${BASE_URL}/services/rest/persistence/reset`);
  check(res, {
    "Reset OK": (r) => r.status === 200,
  });
}

export default function () {
  let csrfToken = null;
  let cookies = {};

  group("Login", () => {

    let res = http.get(`${BASE_URL}/login`);
    let doc = parseHTML(res.body);

    let tokenElement = doc.find("input[name='_csrf']");
    csrfToken = tokenElement.attr("value");

    cookies = res.cookies;

    check(res, {
      "Login page carregada": (r) => r.status === 200,
      "CSRF encontrado": () => csrfToken != null
    }, { cenario: "login" });

    // POST login
    res = http.post(
      `${BASE_URL}/loginAction`,
      {
        username: "user1",
        password: "password",
        action: "login",
        _csrf: csrfToken,
      },
      {
        cookies: cookies,
        redirects: 0,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      },
    );

    check(res, {
      "Login redirect 302": (r) => r.status === 302,
    }, { cenario: "login" });

    // Segue o redirect manualmente
    res = http.get(`${BASE_URL}/`, { cookies: cookies });

    check(res, {
      "Página contém Logout": (r) => r.body.includes("Logout"),
    }, { cenario: "login" });

    sleep(1);
  });

  group("Compra Produto", () => {

    // GET Home
    let res = http.get(`${BASE_URL}/`, { cookies: cookies });
    let doc = parseHTML(res.body);

    let categoryLink = doc.find("a.menulink").first().attr("href");

    if (!categoryLink) {
      console.log("Categoria não encontrada, tentando fallback...");
      return;
    }

    // GET categoria
    res = http.get(`${DOMAIN_URL}${categoryLink}`, { cookies: cookies });
    let docCat = parseHTML(res.body);

    let productLink = docCat.find("div.thumbnail a").first().attr("href");

    if (!productLink) {
      console.log("Produto não encontrado na categoria!");
      return;
    }

    // GET produto
    res = http.get(`${DOMAIN_URL}${productLink}`, { cookies: cookies });
    let docProd = parseHTML(res.body);

    let productId = productLink.includes("id=")
      ? productLink.split("id=")[1]
      : null;

    let productName = docProd.find("h2.product-title").text().trim();

    csrfToken = docProd.find("input[name='_csrf']").attr("value");

    check(res, {
      "Produto OK": () => !!productName,
      "CSRF do produto OK": () => csrfToken != null,
      "ProductId OK": () => productId != null,
    }, { cenario: "compra" });

    sleep(1);

    // POST add to cart
    res = http.post(
      `${BASE_URL}/cartAction`,
      {
        productid: productId,
        addToCart: "Add to Cart",
        _csrf: csrfToken,
      },
      {
        cookies: cookies,
        redirects: 0,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      },
    );

    check(res, {
      "Add to cart redirect OK": (r) => r.status === 302,
    }, { cenario: "compra" });

    sleep(1);

    // GET cart
    res = http.get(`${BASE_URL}/cart`, { cookies: cookies });

    check(res, {
      "Carrinho contém produto": (r) =>
        productName && r.body.includes(productName),
    }, { cenario: "compra" });

    sleep(1);
  });
}
