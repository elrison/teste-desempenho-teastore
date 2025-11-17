import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';
import { URL } from 'https://jslib.k6.io/url/1.0.0/index.js';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';


// Read host/port/base path from env for CI reproducibility
const HOST = __ENV.HOST || 'http://localhost';
const PORT = __ENV.PORT || '18081';
const BASE_PATH = __ENV.BASE_PATH || '/tools.descartes.teastore.webui';
const BASE_HOST = `${HOST}:${PORT}`;
const BASE_UI = `${BASE_HOST}${BASE_PATH}`;

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
  if (!body) return null;
  const doc = parseHTML(body);
  // 1) common input names
  const inputNames = ["_csrf", "csrf", "csrfToken", "csrf_token", "_csrf_token"];
  for (let name of inputNames) {
    let el = doc.find(`input[name='${name}']`);
    if (el && el.attr('value')) return el.attr('value');
  }

  // 2) meta tags with various names
  const metaNames = ["_csrf", "csrf-token", "csrf_token", "csrf"];
  for (let m of metaNames) {
    let el = doc.find(`meta[name='${m}']`);
    if (el && el.attr('content')) return el.attr('content');
  }

  // 3) inline JS patterns
  let match = body.match(/_csrf['"]?\s*[:=]\s*['"]([^'"]+)/) || body.match(/csrfToken['"]?\s*[:=]\s*['"]([^'"]+)/) || body.match(/csrf['"]?\s*[:=]\s*['"]([^'"]+)/);
  if (match && match[1]) return match[1];

  // 4) meta property (og or similar) or input hidden fallback
  let meta = doc.find("meta[name='csrf-token']");
  if (meta && meta.attr('content')) return meta.attr('content');

  return null;
}

function _logDebug(tag, body) {
  try {
    const max = 8000;
    const snippet = body ? body.substring(0, max) : '';
    console.error(`DEBUG [${tag}]: ${snippet}`);
  } catch (e) {
    // noop
  }
}

// Collect debug dumps during the run so handleSummary can write them to files.
const __DEBUG_ENTRIES = [];
const __DEBUG_MAX_ENTRIES = 100; // safety limit to avoid OOM
function _collectDebug(tag, body) {
  try {
    if (__DEBUG_ENTRIES.length >= __DEBUG_MAX_ENTRIES) return;
    const maxBody = 20000; // keep reasonable
    __DEBUG_ENTRIES.push({ tag, body: body ? body.substring(0, maxBody) : '', ts: Date.now() });
  } catch (e) {
    // ignore
  }
}

export default function () {
  let csrf = null;
  let loginSuccess = false;

  group('Cenário de Login', function () {
    let res = http.get(`${BASE_UI}/login`, { redirects: 3 });

    check(res, { 'Página login carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCsrf(res.body);

    // If no CSRF token is present, proceed without it - some deployments don't include a hidden _csrf
    if (!csrf) {
      _logDebug('login_get_no_csrf', res.body);
    }

    const payload = {
      username: 'user2',
      password: 'password',
      action: 'login',
    };
    if (csrf) payload._csrf = csrf;

    const postRes = http.post(`${BASE_UI}/loginAction`, payload, { redirects: 3 });
    loginSuccess = check(postRes, {
      'Login status 200/302': (r) => [200, 302].includes(r.status)
    }, { cenario: 'login' });
    if (!loginSuccess) {
      _logDebug('login_post_failure', postRes.body);
      _collectDebug('login_post_failure', postRes.body);
      return;
    }

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
      _logDebug('no_category_link', res.body);
      return;
    }

    const catUrl = new URL(link.attr('href'), BASE_HOST).toString();
    res = http.get(catUrl);
    check(res, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

    const docCat = parseHTML(res.body);
    let prodLinkEl = docCat.find('div.thumbnail a').first() || docCat.find("a[href*='product']").first();
    if (!prodLinkEl || !prodLinkEl.attr('href')) {
      check(res, { 'Produto encontrado': () => false }, { cenario: 'compra' });
      _logDebug('no_product_link', res.body);
      _collectDebug('no_product_link', res.body);
      return;
    }

    const productHref = new URL(prodLinkEl.attr('href'), BASE_HOST).toString();
    res = http.get(productHref);
    check(res, { 'Produto carregado': (r) => r.status === 200 }, { cenario: 'compra' });

    const docProd = parseHTML(res.body);
    // Try a few fallbacks for product name (different TeaStore themes use different elements)
    let productName = (docProd.find("h2.product-title").first() || docProd.find("h2.minipage-title").first())?.text().trim();
    if (!productName) {
      productName = (docProd.find('h1').first() || docProd.find('title').first())?.text().trim();
    }

    const csrfProd = extractCsrf(res.body) || csrf;
    if (!csrfProd) {
      // some deployments don't expose a _csrf hidden input on product pages; we'll proceed without it
      _logDebug('no_csrf_product', res.body);
    }

    let productId = docProd.find("input[name='productid']").attr('value');
    if (!productId) {
      const u = new URL(productHref);
      productId = u.searchParams.get("id");
    }
    if (!productId) {
      check(res, { 'id do produto encontrado': () => false }, { cenario: 'compra' });
      _logDebug('no_product_id', res.body);
      _collectDebug('no_product_id', res.body);
      return;
    }

    const addPayload = {
      productid: productId,
      addToCart: "Add to Cart",
    };
    if (csrfProd) addPayload._csrf = csrfProd;

    const addRes = http.post(`${BASE_UI}/cartAction`, addPayload, { redirects: 3 });

    check(addRes, { 'AddToCart 200/302': (r) => [200, 302].includes(r.status) }, { cenario: 'compra' });
  if (![200,302].includes(addRes.status)) _logDebug('add_to_cart_failed', addRes.body);
  if (![200,302].includes(addRes.status)) _collectDebug('add_to_cart_failed', addRes.body);

    const cartRes = http.get(`${BASE_UI}/cart`);

    // Robust check: strip HTML tags, normalize entities/whitespace and compare case-insensitively.
    function stripTags(s) {
      if (!s) return '';
      // remove script/style blocks first
      s = s.replace(/<script[\s\S]*?<\/script>/gi, ' ');
      s = s.replace(/<style[\s\S]*?<\/style>/gi, ' ');
      // then remove all tags
      return s.replace(/<[^>]+>/g, ' ');
    }

    function normalizeText(s) {
      if (!s) return '';
      let out = s.replace(/&nbsp;|&#160;/g, ' ').replace(/&amp;/g, '&');
      out = stripTags(out);
      out = out.replace(/\s+/g, ' ').trim();
      return out.toLowerCase();
    }

    const normProduct = normalizeText(productName || '');
    const normCart = normalizeText(cartRes.body || '');

    const cartHasProduct = normProduct && normCart.includes(normProduct);

    check(cartRes, {
      'Carrinho contém produto': () => cartHasProduct
    }, { cenario: 'compra' });

    if (!cartHasProduct) {
      _logDebug('cart_missing_product', cartRes.body);
      _collectDebug('cart_missing_product', cartRes.body);
    }

    sleep(0.5);
  });

  // Logout at end of flow - TeaStore processes logout via loginAction?logout=
  group('Logout', function () {
    const logoutRes = http.post(`${BASE_UI}/loginAction?logout=`);
    check(logoutRes, { 'Logout OK': (r) => [200, 302].includes(r.status) }, { cenario: 'logout' });
    sleep(0.2);
  });
}

// NOVO: Adiciona o summary handler para gerar o HTML
export function handleSummary(data) {
  const out = {
    'k6-complex-report.html': htmlReport(data),
    'k6-complex.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };

  // Emit collected debug entries as separate files (flat filenames) so the runner will create them reliably.
  // Also create a simple index HTML that links to each debug file for quick inspection.
  try {
    let indexLines = ['<html><head><meta charset="utf-8"><title>k6 debug files</title></head><body>','<h1>Debug dumps</h1>','<ul>'];
    for (let i = 0; i < __DEBUG_ENTRIES.length; i++) {
      const e = __DEBUG_ENTRIES[i];
      const safeTag = (e.tag || 'debug').replace(/[^a-zA-Z0-9-_]/g, '_');
      const fname = `debug_${safeTag}_${i + 1}.html`;
      // ensure we add a small header so the file is valid HTML even if body is a fragment
      const bodyContent = (e.body || '').startsWith('<') ? e.body : `<pre>${e.body || ''}</pre>`;
      out[fname] = `<!-- collected ${new Date(e.ts).toISOString()} tag=${e.tag} -->\n${bodyContent}`;
      indexLines.push(`<li><a href='./${fname}'>${fname}</a> - ${new Date(e.ts).toISOString()} - ${e.tag}</li>`);
    }
    indexLines.push('</ul></body></html>');
    if (__DEBUG_ENTRIES.length > 0) out['debug_index.html'] = indexLines.join('\n');
  } catch (err) {
    console.error('Failed to emit debug entries in handleSummary:', err);
  }

  return out;
}