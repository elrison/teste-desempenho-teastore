import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { parseHTML } from 'k6/html';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.9'],
    'checks{cenario:compra}': ['rate>0.9'],
  },
};

const BASE = 'http://localhost:18081/tools.descartes.teastore.webui';

function extractCsrf(html) {
  const doc = parseHTML(html);
  const input = doc.find('input[name="_csrf"]');
  if (input && input.attr('value')) return input.attr('value');
  const meta = doc.find('meta[name="_csrf"]');
  if (meta && meta.attr('content')) return meta.attr('content');
  return null;
}

export default function () {
  const jar = http.cookieJar();
  let csrf = null;
  let productName = '';

  // 1️⃣ Login Page
  group('Login', () => {
    let res = http.get(`${BASE}/login`, { jar });
    check(res, { 'Login page carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCsrf(res.body);
    check(csrf, { 'Token CSRF encontrado': (v) => !!v }, { cenario: 'login' });

    const payload = { username: 'user1', password: 'password', _csrf: csrf };
    res = http.post(`${BASE}/loginAction`, payload, { redirects: 5, jar });
    check(res, { 'Login efetuado': (r) => [200, 302].includes(r.status) }, { cenario: 'login' });
  });

  // 2️⃣ Fluxo de compra
  group('Fluxo de Compra', () => {
    // Home
    let res = http.get(`${BASE}/`, { jar });
    check(res, { 'Home carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docHome = parseHTML(res.body);
    const catLink = docHome.find('a.menulink').first().attr('href');
    check(catLink, { 'Categoria encontrada': (v) => !!v }, { cenario: 'compra' });

    // Categoria
    res = http.get(new URL(catLink, BASE).toString(), { jar });
    check(res, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docCat = parseHTML(res.body);
    const prodLink = docCat.find('div.thumbnail a').first().attr('href');
    check(prodLink, { 'Produto encontrado': (v) => !!v }, { cenario: 'compra' });

    // Produto
    res = http.get(new URL(prodLink, BASE).toString(), { jar });
    check(res, { 'Página do produto carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docProd = parseHTML(res.body);
    const prodId = docProd.find('input[name="productid"]').attr('value');
    csrf = extractCsrf(res.body);
    productName = docProd.find('h2.product-title').text().trim();

    check(prodId, { 'ID do produto encontrado': (v) => !!v }, { cenario: 'compra' });

    // Adicionar ao carrinho
    const cartPayload = { productid: prodId, addToCart: 'Add to Cart', _csrf: csrf };
    res = http.post(`${BASE}/cartAction`, cartPayload, { redirects: 5, jar });
    check(res, { 'Produto adicionado ao carrinho': (r) => [200, 302].includes(r.status) }, { cenario: 'compra' });

    // Validar no carrinho
    res = http.get(`${BASE}/cart`, { jar });
    check(res, { 'Produto está no carrinho': (r) => r.body.includes(productName) }, { cenario: 'compra' });

    sleep(1);
  });
}
