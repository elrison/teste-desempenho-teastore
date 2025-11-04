// NOME DO ARQUIVO: k6-teastore/cenarios-complexos.js

import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

const BASE_URL = "http://localhost:18081/tools.descartes.teastore.webui";
// CORREÇÃO: Esta variável deve apontar para o localhost, pois os links
// extraídos (categoryLink, productLink) são relativos ao domínio.
const DOMAIN_URL = 'http://localhost:18081'; 

export function setup() {
  console.log('--- Resetando base via API ---');
  // O reset usa a BASE_URL completa, o que está correto
  const res = http.post(`${BASE_URL}/services/rest/persistence/reset`);
  check(res, {
    'Reset via API status 200': (r) => r.status === 200,
  });
}

export const options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  let loginSuccess = false;

  group('Cenário de Login', function () {
    http.get(`${BASE_URL}/login`);
    sleep(1);

    const loginPayload = 'username=user1&password=password&action=login';
    const loginParams = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };
    const res = http.post(`${BASE_URL}/loginAction`, loginPayload, loginParams);

    loginSuccess = check(res, {
      'Login funcionou': (r) => r.status === 200,
      'Página contém Logout': (r) => !!r.body && r.body.includes('Logout'),
    });
    sleep(1);
  });

  if (loginSuccess) {
    group('Compra Produto', function () {
      let res = http.get(`${BASE_URL}/`);
      const doc = parseHTML(res.body);

      const categoryLink = doc.find('ul.nav-sidebar a.menulink').first().attr('href');

      if (categoryLink) {
        // CORREÇÃO: Usar DOMAIN_URL + link relativo extraído
        res = http.get(`${DOMAIN_URL}${categoryLink}`);
        const docCat = parseHTML(res.body);

        const productLink = docCat.find('div.thumbnail a').first().attr('href');

        if (productLink) {
          // CORREÇÃO: Usar DOMAIN_URL + link relativo extraído
          res = http.get(`${DOMAIN_URL}${productLink}`);
          const docProd = parseHTML(res.body);

          const productName = docProd.find('h2.product-title').text().trim();
          sleep(1);

          // O productLink é algo como /tools.descartes.teastore.webui/product?id=7
          // Precisamos apenas do ID.
          const productId = productLink.split('id=')[1]; 

          const cartPayload = { productid: productId, action: 'add' };
          // O cartAction usa a BASE_URL, o que está correto
          res = http.post(`${BASE_URL}/cartAction`, cartPayload);

          check(res, {
            'Produto adicionado ao carrinho': (r) => r.status === 200,
          });

          sleep(1);

          res = http.get(`${BASE_URL}/cart`);
          check(res, {
            'Carrinho contém produto': (r) => r.body.includes(productName),
          });
        }
      }
      sleep(1);
    });
  }
}
