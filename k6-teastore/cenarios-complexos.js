import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';


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
    'checks{cenario:login}': ['rate>0.2'], // pipeline-friendly
    'checks{cenario:compra}': ['rate>0.2'],
  },
};

function extractCsrf(body) {
  const doc = parseHTML(body);

  // 1) input
  let el = doc.find("input[name='_csrf']");
  if (el && el.attr('value')) return el.attr('value');

  // 2) meta
  el = doc.find("meta[name='_csrf']");
  if (el && el.attr('content')) return el.attr('content');

  // 3) inline JS
  let match = body.match(/_csrf['"]?\s*[:=]\s*['"]([^'"]+)/);
  if (match && match[1]) return match[1];

  return null;
}

export default function () {
  let csrf = null;
  let loginSuccess = false;

  group('Cenário de Login', function () {
    let res = http.get(`${BASE_UI}/login`, { redirects: 3 });

    check(res, { 'Página login carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCsrf(res.body);

    check(res, { 'CSRF encontrado': () => !!csrf }, { cenario: 'login' });
    if (!csrf) return;

    const payload = {
      username: 'user1',
      password: 'password',
      action: 'login',
      _csrf: csrf,
    };

    const postRes = http.post(`${BASE_UI}/loginAction`, payload, { redirects: 3 });
    loginSuccess = check(postRes, {
      'Login status 200/302': (r) => [200, 302].includes(r.status)
    }, { cenario: 'login' });

    if (!loginSuccess) return;

    const home = http.get(`${BASE_UI}/`, { redirects: 3 });
    csrf = extractCsrf(home.body) || csrf;
    check(home, { 'Home após login ok': (r) => r.status === 200 }, { cenario: 'login' });

    sleep(0.5);
  });

  if (!loginSuccess) return;

  group('Compra Produto', function () {
    let res = http.get(`${BASE_UI}/`);
    check(res, { 'Página inicial ok': (r) => r.status === 200 }, { cenario: 'compra' });

    const doc = parseHTML(res.body);
    let link = doc.find('ul.nav-sidebar a.menulink').first() || doc.find('a.menulink').first();
    if (!link || !link.attr('href')) {
      check(res, { 'Categoria encontrada': () => false }, { cenario: 'compra' });
      return;
    }

    const catUrl = new URL(link.attr('href'), BASE_HOST).toString();
    res = http.get(catUrl);
    check(res, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docCat = parseHTML(res.body);
    let prodLinkEl = docCat.find('div.thumbnail a').first() || docCat.find("a[href*='product']").first();
    if (!prodLinkEl || !prodLinkEl.attr('href')) {
      check(res, { 'Produto encontrado': () => false }, { cenario: 'compra' });
      return;
    }

    const productHref = new URL(prodLinkEl.attr('href'), BASE_HOST).toString();
    res = http.get(productHref);
    check(res, { 'Produto carregado': (r) => r.status === 200 }, { cenario: 'compra' });

    const docProd = parseHTML(res.body);
    const productName = (docProd.find("h2.product-title").first() || docProd.find("h2.minipage-title").first())?.text().trim();

    const csrfProd = extractCsrf(res.body) || csrf;
    if (!csrfProd) {
      check(res, { 'CSRF produto encontrado': () => false }, { cenario: 'compra' });
      return;
    }

    let productId = docProd.find("input[name='productid']").attr('value');
    if (!productId) {
      const u = new URL(productHref);
      productId = u.searchParams.get("id");
    }
    if (!productId) {
      check(res, { 'id do produto encontrado': () => false }, { cenario: 'compra' });
      return;
    }

    const addRes = http.post(`${BASE_UI}/cartAction`, {
      productid: productId,
      addToCart: "Add to Cart",
      _csrf: csrfProd,
    }, { redirects: 3 });

    check(addRes, { 'AddToCart 200/302': (r) => [200, 302].includes(r.status) }, { cenario: 'compra' });

    const cartRes = http.get(`${BASE_UI}/cart`);
    check(cartRes, {
      'Carrinho contém produto': (r) => productName && r.body.includes(productName)
    }, { cenario: 'compra' });

    sleep(0.5);
  });
}

// NOVO: Adiciona o summary handler para gerar o HTML
export function handleSummary(data) {
  return {
    'k6-complex-report.html': htmlReport(data),
    'k6-complex.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}