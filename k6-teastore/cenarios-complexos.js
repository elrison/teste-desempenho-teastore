import http from 'k6/http';
import { sleep, check, group } from 'k6';

const BASE_URL = 'http://localhost:18081/tools.descartes.teastore.webui';
const HOST_URL = 'http://localhost:18081';

export function setup() {
  console.log('Resetando banco via API REST...');
  const res = http.post(`${BASE_URL}/services/rest/persistence/resetDB`);
  check(res, { 'reset OK (200)': (r) => r.status === 200 });
}

export const options = {
  vus: 5,
  duration: '30s',
};

export default function () {

  group('Login', () => {
    http.get(`${BASE_URL}/login`);

    const loginPayload = 'username=user1&password=password&action=login';
    const params = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };

    const res = http.post(`${BASE_URL}/loginAction`, loginPayload, params);

    check(res, {
      'status 200': (r) => r.status === 200,
      'Logout aparece': (r) => r.body && r.body.includes('Logout'),
    });
  });

  group('Carrinho via API REST', () => {

    const products = http
      .get(`${BASE_URL}/services/rest/product/3`)
      .json();

    check(products, { 'produtos OK': (p) => p.length > 0 });

    const product = products[0];

    const cartRes = http.post(`${BASE_URL}/cartAction`, {
      productid: product.id,
      action: 'add',
    });

    check(cartRes, {
      'add cart OK': (r) => r.status === 200,
    });

    const cartPage = http.get(`${BASE_URL}/cart`);
    check(cartPage, {
      'produto no carrinho': (r) => r.body && r.body.includes(product.title),
    });
  });

  sleep(1);
}
