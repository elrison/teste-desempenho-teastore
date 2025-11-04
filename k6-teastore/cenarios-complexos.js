import http from 'k6/http';
import { sleep, check, group } from 'k6';
import { parseHTML } from 'k6/html';

const BASE_URL = 'http://teastore-webui:8080/tools.descartes.teastore.webui';
const HOST_URL = 'http://teastore-webui:8080';

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
        res = http.get(`${HOST_URL}${categoryLink}`);
        const docCat = parseHTML(res.body);

        const productLink = docCat.find('div.thumbnail a').first().attr('href');

        if (productLink) {
          res = http.get(`${HOST_URL}${productLink}`);
          const docProd = parseHTML(res.body);

          const productName = docProd.find('h2.product-title').text().trim();
          sleep(1);

          const productId = productLink.split('id=')[1];

          const cartPayload = { productid: productId, action: 'add' };
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
