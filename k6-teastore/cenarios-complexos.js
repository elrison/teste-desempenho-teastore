import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';

const BASE_UI = "http://localhost:18081/tools.descartes.teastore.webui";
const BASE_HOST = "http://localhost:18081";

export function setup() {
  console.log('--- Resetando base via API ---');
  const res = http.post(`${BASE_UI}/services/rest/persistence/reset`);
  check(res, { 'Reset via API status 200': (r) => r.status === 200 });
}

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.5'],
    'checks{cenario:compra}': ['rate>0.5'],
  },
};

function extractCsrfFromBody(body) {
  const doc = parseHTML(body);
  let el = doc.find("input[name='_csrf']");
  if (el && el.attr('value')) return el.attr('value');
  el = doc.find("meta[name='_csrf']");
  if (el && el.attr('content')) return el.attr('content');
  // fallback: search for "_csrf" pattern in JS
  const m = body.match(/_csrf['"]?\s*[:=]\s*['"]([^'"]+)['"]/);
  if (m) return m[1];
  return null;
}

export default function () {
  let csrf = null;
  let loginSuccess = false;

  group('Cenário de Login', function () {
    let res = http.get(`${BASE_UI}/login`, { redirects: 5 });
    check(res, { 'Página login carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCsrfFromBody(res.body);
    if (!csrf) {
      check(res, { 'CSRF encontrado': () => false }, { cenario: 'login' });
      return;
    }
    check({ ok: true }, { 'CSRF encontrado': () => !!csrf }, { cenario: 'login' });

    const payload = {
      username: 'user1',
      password: 'password',
      action: 'login',
      _csrf: csrf,
    };
    const postRes = http.post(`${BASE_UI}/loginAction`, payload, { redirects: 5 });
    loginSuccess = check(postRes, {
      'Login status 200 or 302': (r) => r.status === 200 || r.status === 302,
    }, { cenario: 'login' });

    if (!loginSuccess) return;

    // validate by loading home
    const home = http.get(`${BASE_UI}/`, { redirects: 5 });
    csrf = extractCsrfFromBody(home.body) || csrf;
    check(home, { 'Home after login ok': (r) => r.status === 200 }, { cenario: 'login' });
    sleep(1);
  });

  if (!loginSuccess) return;

  group('Compra Produto', function () {
    let res = http.get(`${BASE_UI}/`);
    check(res, { 'Página inicial ok': (r) => r.status === 200 }, { cenario: 'compra' });

    const doc = parseHTML(res.body);
    let link = doc.find('ul.nav-sidebar a.menulink').first();
    if (!link || !link.attr('href')) link = doc.find('a.menulink').first();
    if (!link || !link.attr('href')) {
      check(res, { 'Categoria encontrada': () => false }, { cenario: 'compra' });
      return;
    }
    let categoryHref = link.attr('href');
    const catUrl = new URL(categoryHref, BASE_HOST).toString();
    res = http.get(catUrl);
    check(res, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docCat = parseHTML(res.body);
    let prodLinkEl = docCat.find('div.thumbnail a').first();
    if (!prodLinkEl || !prodLinkEl.attr('href')) prodLinkEl = docCat.find('a[href*="product"]').first();
    if (!prodLinkEl || !prodLinkEl.attr('href')) {
      check(res, { 'Produto encontrado': () => false }, { cenario: 'compra' });
      return;
    }
    const productHref = new URL(prodLinkEl.attr('href'), BASE_HOST).toString();
    res = http.get(productHref);
    check(res, { 'Produto carregado': (r) => r.status === 200 }, { cenario: 'compra' });

    const docProd = parseHTML(res.body);
    const productNameEl = docProd.find('h2.product-title').first() || docProd.find('h2.minipage-title').first();
    const productName = productNameEl ? productNameEl.text().trim() : null;

    const csrfProd = extractCsrfFromBody(res.body) || csrf;
    if (!csrfProd) {
      check(res, { 'Falha ao extrair CSRF do produto': () => false }, { cenario: 'compra' });
      return;
    }

    let productId = null;
    const idEl = docProd.find("input[name='productid']").first();
    if (idEl && idEl.attr('value')) productId = idEl.attr('value');
    if (!productId) {
      const u = new URL(productHref);
      productId = u.searchParams.get('id');
    }
    if (!productId) {
      check(res, { 'product id encontrado': () => false }, { cenario: 'compra' });
      return;
    }

    const cartPayload = {
      productid: productId,
      addToCart: 'Add to Cart',
      _csrf: csrfProd,
    };
    const addRes = http.post(`${BASE_UI}/cartAction`, cartPayload, { redirects: 5 });
    check(addRes, { 'Produto adicionado ao carrinho (POST)': (r) => r.status === 200 || r.status === 302 }, { cenario: 'compra' });

    sleep(1);
    const cartRes = http.get(`${BASE_UI}/cart`);
    check(cartRes, {
      'Carrinho contém produto': (r) => productName && r.body && r.body.includes(productName)
    }, { cenario: 'compra' });

    sleep(1);
  });
}
