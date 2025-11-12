import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { parseHTML } from 'k6/html';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.9'],
    'checks{cenario:compra}': ['rate>0.9'],
  },
};

const BASE_UI = 'http://localhost:18081/tools.descartes.teastore.webui';
const BASE_HOST = 'http://localhost:18081';

function extractCSRF(body) {
  const doc = parseHTML(body);
  let token = doc.find("input[name='_csrf']").first();
  if (token && token.attr('value')) return token.attr('value');

  // fallback: meta tag
  token = doc.find("meta[name='_csrf']").first();
  if (token && token.attr('content')) return token.attr('content');

  // fallback: JS inline (some versions embed window._csrf)
  const match = body.match(/_csrf['"]?\s*[:=]\s*['"]([^'"]+)['"]/);
  if (match) return match[1];
  return null;
}

export default function () {
  let csrf = null;
  let productName = null;

  group('Cenário de Login', function () {
    let res = http.get(`${BASE_UI}/login`, { redirects: 5 });
    check(res, { 'Login page carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCSRF(res.body);
    check(res, { 'Token CSRF encontrado': () => !!csrf }, { cenario: 'login' });

    if (!csrf) {
      return;
    }

    const payload = {
      username: 'user1',
      password: 'password',
      _csrf: csrf,
      action: 'login',
    };

    const loginRes = http.post(`${BASE_UI}/loginAction`, payload, { redirects: 5 });
    check(loginRes, { 'Login efetuado': (r) => [200, 302].includes(r.status) }, { cenario: 'login' });

    const home = http.get(`${BASE_UI}/`, { redirects: 5 });
    check(home, { 'Home carregada': (r) => r.status === 200 }, { cenario: 'login' });
    csrf = extractCSRF(home.body) || csrf;
    sleep(1);
  });

  // caso login falhe, aborta o cenário
  if (!csrf) return;

  group('Cenário de Compra', function () {
    // 1️⃣ Home
    let res = http.get(`${BASE_UI}/`);
    check(res, { 'Página inicial ok': (r) => r.status === 200 }, { cenario: 'compra' });

    const docHome = parseHTML(res.body);
    let categoryLink = docHome.find('ul.nav-sidebar a.menulink').first().attr('href');
    if (!categoryLink) {
      categoryLink = docHome.find('a.menulink').first().attr('href');
    }
    check(res, { 'Categoria encontrada': () => !!categoryLink }, { cenario: 'compra' });

    if (!categoryLink) return;

    // 2️⃣ Categoria
    const catUrl = categoryLink.startsWith('http') ? categoryLink : `${BASE_HOST}${categoryLink}`;
    res = http.get(catUrl);
    check(res, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docCat = parseHTML(res.body);
    const productLink = docCat.find('div.thumbnail a').first().attr('href');
    check(res, { 'Produto encontrado': () => !!productLink }, { cenario: 'compra' });
    if (!productLink) return;

    // 3️⃣ Produto
    const prodUrl = productLink.startsWith('http') ? productLink : `${BASE_HOST}${productLink}`;
    res = http.get(prodUrl);
    check(res, { 'Página do produto carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docProd = parseHTML(res.body);
    productName = docProd.find('h2.product-title').first().text() ||
                  docProd.find('h2.minipage-title').first().text();
    check(res, { 'Nome do produto encontrado': () => !!productName }, { cenario: 'compra' });

    const idInput = docProd.find("input[name='productid']").first();
    const productId = idInput ? idInput.attr('value') : null;
    check(res, { 'ID do produto encontrado': () => !!productId }, { cenario: 'compra' });

    const csrfProd = extractCSRF(res.body) || csrf;
    check(res, { 'CSRF do produto encontrado': () => !!csrfProd }, { cenario: 'compra' });
    if (!csrfProd || !productId) return;

    // 4️⃣ Adiciona ao carrinho
    const cartPayload = {
      productid: productId,
      addToCart: 'Add to Cart',
      _csrf: csrfProd,
    };
    const addRes = http.post(`${BASE_UI}/cartAction`, cartPayload, { redirects: 5 });
    check(addRes, {
      'Produto adicionado ao carrinho': (r) => [200, 302].includes(r.status),
    }, { cenario: 'compra' });

    // 5️⃣ Valida carrinho
    const cartRes = http.get(`${BASE_UI}/cart`);
    check(cartRes, {
      'Produto está no carrinho': (r) => r.status === 200 && r.body.includes(productName),
    }, { cenario: 'compra' });

    sleep(1);
  });
}
