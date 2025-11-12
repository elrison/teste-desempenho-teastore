import http from 'k6/http';
import { sleep, check, group } from 'k6';
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

// ============================================
// Função para extrair o token CSRF
// ============================================
function extractCsrf(body) {
  const doc = parseHTML(body);
  const input = doc.find("input[name='_csrf']").first();
  if (input && input.attr('value')) return input.attr('value');
  return null;
}

// ============================================
// Cenário completo de navegação
// ============================================
export default function () {
  let csrf = null;
  let cookies = null;
  let productName = null;

  group('Cenário de Login', () => {
    // GET /login
    let res = http.get(`${BASE}/login`);
    check(res, { 'Login page carregada': (r) => r.status === 200 }, { cenario: 'login' });

    csrf = extractCsrf(res.body);
    check(res, { 'Token CSRF encontrado': () => !!csrf }, { cenario: 'login' });

    if (!csrf) {
      console.error('❌ Falha ao capturar CSRF no login');
      return;
    }

    cookies = res.cookies;

    // POST /loginAction
    const payload = {
      username: 'user1',
      password: 'password',
      action: 'login',
      _csrf: csrf,
    };
    const loginRes = http.post(`${BASE}/loginAction`, payload, {
      cookies,
      redirects: 3,
      tags: { cenario: 'login' },
    });
    check(loginRes, {
      'Login efetuado': (r) => r.status === 200 || r.status === 302,
    }, { cenario: 'login' });

    sleep(1);
  });

  // ============================================
  // NAVEGAÇÃO PÓS-LOGIN
  // ============================================
  group('Cenário de Compra', () => {
    // HOME
    let home = http.get(`${BASE}/`);
    check(home, { 'Home carregada': (r) => r.status === 200 }, { cenario: 'compra' });
    csrf = extractCsrf(home.body) || csrf;
    const docHome = parseHTML(home.body);

    // Categoria
    let categoryLink = docHome.find('ul.nav-sidebar a.menulink').first();
    if (!categoryLink || !categoryLink.attr('href')) {
      console.error('❌ Categoria não encontrada');
      return;
    }

    const categoryUrl = new URL(categoryLink.attr('href'), BASE).toString();
    let catRes = http.get(categoryUrl);
    check(catRes, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });
    csrf = extractCsrf(catRes.body) || csrf;

    // Produto
    const docCat = parseHTML(catRes.body);
    const prodLink = docCat.find('div.thumbnail a').first();
    if (!prodLink || !prodLink.attr('href')) {
      console.error('❌ Produto não encontrado');
      return;
    }
    const prodUrl = new URL(prodLink.attr('href'), BASE).toString();

    const prodRes = http.get(prodUrl);
    check(prodRes, { 'Página do produto carregada': (r) => r.status === 200 }, { cenario: 'compra' });
    csrf = extractCsrf(prodRes.body) || csrf;

    const docProd = parseHTML(prodRes.body);
    const prodNameEl = docProd.find('h2.product-title').first() || docProd.find('h2.minipage-title').first();
    productName = prodNameEl ? prodNameEl.text().trim() : null;

    const idEl = docProd.find("input[name='productid']").first();
    const productId = idEl ? idEl.attr('value') : null;

    check(prodRes, { 'ID do produto encontrado': () => !!productId }, { cenario: 'compra' });

    if (!productId) {
      console.error('❌ Produto sem ID');
      return;
    }

    // Adiciona ao carrinho
    const cartPayload = {
      productid: productId,
      addToCart: 'Add to Cart',
      _csrf: csrf,
    };
    const addRes = http.post(`${BASE}/cartAction`, cartPayload, {
      redirects: 3,
      tags: { cenario: 'compra' },
    });
    check(addRes, {
      'Produto adicionado ao carrinho': (r) => r.status === 200 || r.status === 302,
    }, { cenario: 'compra' });

    // Verifica carrinho
    const cartRes = http.get(`${BASE}/cart`);
    check(cartRes, {
      'Produto está no carrinho': (r) => productName && r.body.includes(productName),
    }, { cenario: 'compra' });

    sleep(1);
  });
}
