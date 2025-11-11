// NOME DO ARQUIVO: k6-teastore/cenarios-complexos.js

import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

const BASE_URL = "http://localhost:18081/tools.descartes.teastore.webui";
const DOMAIN_URL = "http://localhost:18081";

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.9'],
    'checks{cenario:compra}': ['rate>0.9'],
  },
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

  group('Cenário de Login', function () {

    // 1. GET /login
    let res = http.get(`${BASE_URL}/login`);
    let doc = parseHTML(res.body);

    // extrai CSRF
    let token = doc.find("input[name='_csrf']");
    csrfToken = token.attr('value');

    // captura cookies
    cookies = res.cookies;

    check(res, {
      "Página login carregada": (r) => r.status === 200,
      "CSRF encontrado": () => csrfToken !== null,
    }, {cenario:"login"});

    // 2. POST login
    res = http.post(`${BASE_URL}/loginAction`,
      {
        username: "user1",
        password: "password",
        action: "login",
        _csrf: csrfToken
      },
      {
        cookies: cookies,
        redirects: 0, // NÃO seguir redirect automaticamente
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      });

    check(res, {
      "Login retornou redirect 302": (r) => r.status === 302,
    }, {cenario:"login"});

    // depois do redirect, segue manualmente
    res = http.get(`${BASE_URL}/`,
      { cookies: cookies });

    check(res, {
      "Página contém Logout": (r) => r.body.includes("Logout"),
    }, {cenario:"login"});

    sleep(1);
  });


  group("Compra Produto", function () {

    // Home
    let res = http.get(`${BASE_URL}/`, { cookies: cookies });
    let doc = parseHTML(res.body);

    const categoryLink = doc.find("ul.nav-sidebar a.menulink").first().attr("href");
    res = http.get(`${DOMAIN_URL}${categoryLink}`, { cookies: cookies });

    const docCat = parseHTML(res.body);
    const productLink = docCat.find("div.thumbnail a").first().attr("href");

    res = http.get(`${DOMAIN_URL}${productLink}`, { cookies: cookies });
    const docProd = parseHTML(res.body);

    const productName = docProd.find("h2.product-title").text().trim();
    const productId = productLink.split("id=")[1];

    // novo CSRF
    csrfToken = docProd.find("input[name='_csrf']").attr('value');

    check(res, {
      "Produto carregado": (r) => productName !== "",
      "CSRF do produto capturado": () => csrfToken !== null,
    }, {cenario:"compra"});

    sleep(1);

    // POST Add To Cart
    res = http.post(`${BASE_URL}/cartAction`,
      {
        productid: productId,
        addToCart: "Add to Cart",
        _csrf: csrfToken
      },
      {
        cookies: cookies,
        redirects: 0,
        headers: { "Content-Type": "application/x-www-form-urlencoded" }
      });

    check(res, {
      "AddToCart retornou redirect 302": (r) => r.status === 302,
    }, {cenario:"compra"});

    sleep(1);

    // Ver carrinho
    res = http.get(`${BASE_URL}/cart`, { cookies: cookies });

    check(res, {
      "Carrinho contém produto": (r) => r.body.includes(productName),
    }, {cenario:"compra"});

    sleep(1);
  });
}
