import http from 'k6/http';
import { sleep, check, group } from 'k6';

const HOST = 'http://localhost:18081/tools.descartes.teastore.webui';

// Setup executado 1x antes de tudo
export function setup() {
  const res = http.post(`${HOST}/services/rest/persistence/reset`);
  check(res, {
    'reset DB OK': (r) => r.status === 200,
  });
}

export const options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  group('Login', () => {
    http.get(`${HOST}/login`);
    const payload = 'username=user1&password=password&action=login';
    const params = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };

    const res = http.post(`${HOST}/loginAction`, payload, params);

    check(res, {
      'login OK': (r) => r.status === 200,
      'logout visível': (r) => r.body.includes('Logout'),
    });
  });

  group('Compra via REST', () => {
    // 1. Pega categorias
    let res = http.get(`${HOST}/services/rest/category/`);
    let categories = res.json();

    check(res, {
      'categorias carregadas': (r) => categories.length > 0,
    });

    let category = categories[0];

    // 2. Pega produtos dessa categoria
    res = http.get(`${HOST}/services/rest/product?categoryid=${category}&page=1&number=12`);
    let products = res.json();

    check(res, {
      'produtos carregados': (r) => products.length > 0,
    });

    let product = products[0];

    // 3. Adiciona ao carrinho
    const cartPayload = {
      productid: product.id,
      action: 'add',
    };

    res = http.post(`${HOST}/cartAction`, cartPayload);
    check(res, {
      'produto adicionado no carrinho': (r) => r.status === 200,
    });

    // 4. Verifica carrinho
    res = http.get(`${HOST}/cart`);
    check(res, {
      'produto aparece no carrinho': (r) =>
        r.body.includes(product.title || product.name),
    });
  });

  sleep(1);
}
