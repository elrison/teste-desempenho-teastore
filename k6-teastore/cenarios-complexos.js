// NOME DO ARQUIVO: k6-teastore/cenarios-complexos.js

import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

// CORREÇÃO 1: Usar localhost:18081 para todas as URLs base
const BASE_URL = "http://localhost:18081/tools.descartes.teastore.webui";
const DOMAIN_URL = 'http://localhost:18081';

export function setup() {
  console.log('--- Resetando base via API ---');
  const res = http.post(`${BASE_URL}/services/rest/persistence/reset`);
  check(res, {
    'Reset via API status 200': (r) => r.status === 200,
  });
}

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'checks{cenario:login}': ['rate>0.9'], // Pelo menos 90% dos logins devem funcionar
    'checks{cenario:compra}': ['rate>0.9'], // Pelo menos 90% das compras devem funcionar
  },
};

export default function () {
  let loginSuccess = false;
  let csrfToken = null;

  group('Cenário de Login', function () {
    // 1. GET na página de login para extrair o CSRF
    let res = http.get(`${BASE_URL}/login`);
    let doc = parseHTML(res.body);
    let tokenElement = doc.find("input[name='_csrf']");

    if (tokenElement && tokenElement.attr('value')) {
      csrfToken = tokenElement.attr('value');
    } else {
      check(res, { 'Falha ao extrair CSRF do login': () => false }, { cenario: 'login' });
      return; // Aborta este VU se não achar o token
    }

    // 2. POST de Login com CSRF
    const loginPayload = {
      username: 'user1',
      password: 'password',
      action: 'login',
      _csrf: csrfToken, // <-- CORREÇÃO 2: Adicionar CSRF
    };

    res = http.post(`${BASE_URL}/loginAction`, loginPayload);

    loginSuccess = check(res, {
      'Login status 200': (r) => r.status === 200,
      'Página contém Logout': (r) => r.body && r.body.includes('Logout'),
    }, { cenario: 'login' });
    
    sleep(1);
  });

  if (loginSuccess) {
    group('Compra Produto', function () {
      // 1. Acessa a Home
      let res = http.get(`${BASE_URL}/`);
      const doc = parseHTML(res.body);
      const categoryLink = doc.find('ul.nav-sidebar a.menulink').first().attr('href');

      if (categoryLink) {
        // 2. Acessa a Categoria
        res = http.get(`${DOMAIN_URL}${categoryLink}`); // CORREÇÃO 1: Usar DOMAIN_URL
        const docCat = parseHTML(res.body);
        const productLink = docCat.find('div.thumbnail a').first().attr('href');

        if (productLink) {
          // 3. Acessa o Produto
          res = http.get(`${DOMAIN_URL}${productLink}`); // CORREÇÃO 1: Usar DOMAIN_URL
          const docProd = parseHTML(res.body);
          const productName = docProd.find('h2.product-title').text().trim();
          
          // Extrai o ID do produto do link
          const productId = productLink.split('id=')[1];
          
          // CORREÇÃO 2: Extrai o CSRF da página do produto
          let tokenElement = docProd.find("input[name='_csrf']");
          if (tokenElement && tokenElement.attr('value')) {
            csrfToken = tokenElement.attr('value'); // Atualiza o token
          } else {
            check(res, { 'Falha ao extrair CSRF do produto': () => false }, { cenario: 'compra' });
            return; // Aborta
          }
          sleep(1);
          
          // 4. Adiciona ao Carrinho
          const cartPayload = {
            productid: productId,
            addToCart: 'Add to Cart', // <-- CORREÇÃO 3: Payload correto do form
            _csrf: csrfToken, // <-- CORREÇÃO 2: Adicionar CSRF
          };
          
          res = http.post(`${BASE_URL}/cartAction`, cartPayload);

          check(res, {
            'Produto adicionado ao carrinho (POST)': (r) => r.status === 200,
          }, { cenario: 'compra' });

          sleep(1);

          // 5. Verifica o Carrinho
          res = http.get(`${BASE_URL}/cart`);
          check(res, {
            'Carrinho contém produto': (r) => r.body && r.body.includes(productName),
          }, { cenario: 'compra' });
        }
      }
      sleep(1);
    });
  }
}
