// NOME DO ARQUIVO: k6-teastore/cenarios-complexos.js

import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

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
    'checks{cenario:login}': ['rate>0.9'], 
    'checks{cenario:compra}': ['rate>0.9'], 
  },
};

export default function () {
  let loginSuccess = false;
  let csrfToken = null;

  group('Cenário de Login', function () {
    // 1. GET na página de login
    let res = http.get(`${BASE_URL}/login`);
    
    // ======================================================
    // === DEBUG: IMPRIMIR O HTML DA PÁGINA DE LOGIN =======
    // ======================================================
    if (__VU === 1 && __ITER === 0) { // Imprime apenas uma vez
        console.log('--- DEBUG: Resposta do /login ---');
        console.log(res.body);
        console.log('--- FIM DEBUG ---');
    }
    // ======================================================

    let doc = parseHTML(res.body);
    let tokenElement = doc.find("input[name='_csrf']");

    if (tokenElement && tokenElement.attr('value')) {
      csrfToken = tokenElement.attr('value');
    } else {
      check(res, { 'Falha ao extrair CSRF do login': () => false }, { cenario: 'login' });
      return; 
    }

    // 2. POST de Login com CSRF
    const loginPayload = {
      username: 'user1',
      password: 'password',
      action: 'login',
      _csrf: csrfToken, 
    };

    res = http.post(`${BASE_URL}/loginAction`, loginPayload);

    loginSuccess = check(res, {
      'Login status 200': (r) => r.status === 200,
      'Página contém Logout': (r) => r.body && r.body.includes('Logout'),
    }, { cenario: 'login' });
    
    sleep(1);
  });

  if (loginSuccess) {
    // O resto do script (compra) continua o mesmo...
    group('Compra Produto', function () {
      let res = http.get(`${BASE_URL}/`);
      let doc = parseHTML(res.body);
      const categoryLink = doc.find('ul.nav-sidebar a.menulink').first().attr('href');

      if (categoryLink) {
        res = http.get(`${DOMAIN_URL}${categoryLink}`); 
        const docCat = parseHTML(res.body);
        const productLink = docCat.find('div.thumbnail a').first().attr('href');

        if (productLink) {
          res = http.get(`${DOMAIN_URL}${productLink}`);
          const docProd = parseHTML(res.body);
          
          if (!docProd) {
            check(res, { 'Falha ao carregar página do produto': () => false }, { cenario: 'compra' });
            return;
          }
          
          const productNameElement = docProd.find('h2.product-title');
          const productName = productNameElement ? productNameElement.text().trim() : '';
          
          const productId = productLink.split('id=')[1];
          
          let tokenElement = docProd.find("input[name='_csrf']");
          if (tokenElement && tokenElement.attr('value')) {
            csrfToken = tokenElement.attr('value'); 
          } else {
            check(res, { 'Falha ao extrair CSRF do produto': () => false }, { cenario: 'compra' });
            return; 
          }
          sleep(1);
          
          const cartPayload = {
            productid: productId,
            addToCart: 'Add to Cart', 
            _csrf: csrfToken, 
          };
          
          res = http.post(`${BASE_URL}/cartAction`, cartPayload);

          check(res, {
            'Produto adicionado ao carrinho (POST)': (r) => r.status === 200,
          }, { cenario: 'compra' });

          sleep(1);

          res = http.get(`${BASE_URL}/cart`);
          check(res, {
            'Carrinho contém produto': (r) => r.body && productName && r.body.includes(productName),
          }, { cenario: 'compra' });
        }
      }
      sleep(1);
    });
  }
}