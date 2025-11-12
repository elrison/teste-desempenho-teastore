import http from 'k6/http';
import { check, sleep } from 'k6';
import { parseHTML } from 'k6/html';
import { fail } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.5'],
    'checks{cenario:compra}': ['rate>0.5'],
  },
};

const BASE_URL = 'http://localhost:18081/tools.descartes.teastore.webui';

// --- Aguarda o TeaStore estar disponível ---
function waitForTeaStoreReady() {
  for (let i = 0; i < 60; i++) {
    const res = http.get(`${BASE_URL}/login`);
    if (res.status === 200 && res.body.includes('_csrf')) {
      console.log('✅ TeaStore pronto.');
      return;
    }
    console.log('⏳ Aguardando TeaStore (tentativa ' + (i + 1) + ')...');
    sleep(3);
  }
  fail('❌ TeaStore não ficou pronto após 3 minutos.');
}

// --- Extrai CSRF de qualquer página ---
function extractCsrf(html) {
  const doc = parseHTML(html);
  const input = doc.find('input[name="_csrf"]');
  if (input && input.attr('value')) return input.attr('value');
  return null;
}

export default function () {
  if (__ITER == 0) waitForTeaStoreReady();

  // 1️⃣ LOGIN PAGE
  const loginPage = http.get(`${BASE_URL}/login`);
  check(loginPage, { 'Login page carregada': (r) => r.status === 200 }, { cenario: 'login' });

  const csrfToken = extractCsrf(loginPage.body);
  if (!csrfToken) {
    console.error('❌ Falha ao capturar CSRF no login');
    return;
  }

  // 2️⃣ LOGIN ACTION
  const loginRes = http.post(`${BASE_URL}/loginAction`, {
    username: 'user1',
    password: 'password',
    _csrf: csrfToken,
  });
  check(loginRes, { 'Login efetuado': (r) => r.status === 200 || r.status === 302 }, { cenario: 'login' });

  // 3️⃣ HOME
  const home = http.get(`${BASE_URL}/`);
  check(home, { 'Home carregada': (r) => r.status === 200 }, { cenario: 'compra' });

  // 4️⃣ CATEGORIA
  const categoryMatch = home.body.match(/\/tools\.descartes\.teastore\.webui\/category\?categoryId=\d+/);
  if (!categoryMatch) {
    console.error('❌ Categoria não encontrada');
    return;
  }
  const categoryUrl = categoryMatch[0];
  const categoryRes = http.get(categoryUrl);
  check(categoryRes, { 'Categoria carregada': (r) => r.status === 200 }, { cenario: 'compra' });

  // 5️⃣ PRODUTO
  const productMatch = categoryRes.body.match(/\/tools\.descartes\.teastore\.webui\/product\?id=\d+/);
  if (!productMatch) {
    console.error('❌ Produto não encontrado');
    return;
  }
  const productUrl = productMatch[0];
  const productRes = http.get(productUrl);
  check(productRes, { 'Página do produto carregada': (r) => r.status === 200 }, { cenario: 'compra' });

  // 6️⃣ ADICIONAR AO CARRINHO
  const csrfProduct = extractCsrf(productRes.body);
  const productIdMatch = productUrl.match(/id=(\d+)/);
  const productId = productIdMatch ? productIdMatch[1] : null;

  if (!csrfProduct || !productId) {
    console.error('❌ Falha ao capturar dados do produto');
    return;
  }

  const cartRes = http.post(`${BASE_URL}/cartAction`, {
    addToCart: productId,
    _csrf: csrfProduct,
  });
  check(cartRes, { 'Produto adicionado ao carrinho': (r) => r.status === 200 || r.status === 302 }, { cenario: 'compra' });

  // 7️⃣ VALIDAR CARRINHO
  const cartPage = http.get(`${BASE_URL}/cart`);
  check(cartPage, { 'Produto está no carrinho': (r) => r.status === 200 && r.body.includes('Cart') }, { cenario: 'compra' });

  sleep(1);
}
