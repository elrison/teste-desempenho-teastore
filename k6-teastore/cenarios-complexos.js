import http from 'k6/http';
import { sleep, check, group } from 'k6';

const BASE_URL = 'http://host.docker.internal:18081/tools.descartes.teastore.webui';
const HOST_URL = 'http://host.docker.internal:18081';

// Esta função especial roda UMA VEZ no início do teste e está FUNCIONANDO.
export function setup() {
  console.log('--- Preparando ambiente de teste: Resetando a base de dados via API ---');
  const res = http.post(`${BASE_URL}/services/rest/persistence/reset`);
  check(res, {
    'base de dados foi resetada com sucesso via API (status 200)': (r) => r.status === 200,
  });
  console.log('--- Ambiente de teste pronto ---');
}

// 1. OPÇÕES DO TESTE
export const options = {
  vus: 10,
  duration: '30s',
};

// 2. CENÁRIO DE TESTE PRINCIPAL
export default function () {
  let loginSuccess = false;
  group('Cenário de Login', function () {
    http.get(`${BASE_URL}/login`);
    sleep(1);

    const loginPayload = 'username=user1&password=password&action=login';
    const loginParams = { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } };
    const res = http.post(`${BASE_URL}/loginAction`, loginPayload, loginParams);

    loginSuccess = check(res, {
      'login redirecionou para a página inicial': (r) => r.url.endsWith('/tools.descartes.teastore.webui/'),
      'página pós-login contém "Logout"': (r) => r.body.includes('Logout'),
    });
    sleep(1);
  });

  if (loginSuccess) {
    group('Cenário de Compra', function () {
      let res = http.get(BASE_URL + '/');
      const categoryLink = res.html().find('ul.nav-sidebar a.menulink').first().attr('href');
      
      if (categoryLink) {
        res = http.get(`${HOST_URL}${categoryLink}`);
        const productLink = res.html().find('div.thumbnail a').first().attr('href');
        let productId = null;
        if (productLink) {
          productId = productLink.split('id=')[1];
        }
        
        if (productId) {
          // Visita a página do produto para pegar o nome
          res = http.get(`${HOST_URL}${productLink}`);
          check(res, { 'página do produto carregou': (r) => r.status === 200 });

          // Extrai o nome do produto para uma verificação mais robusta
          const productName = res.html().find('h2.product-title').text().trim();
          sleep(1);

          // Adiciona o produto ao carrinho
          const cartPayload = {
            productid: productId,
            action: 'add',
          };
          res = http.post(`${BASE_URL}/cartAction`, cartPayload);
          check(res, { 'POST para adicionar ao carrinho foi aceito (status 200)': (r) => r.status === 200 });
          sleep(1);

          // CORREÇÃO FINAL: Visita a página do carrinho para verificar o conteúdo.
          res = http.get(`${BASE_URL}/cart`);
          check(res, {
            'página do carrinho contém o nome do produto adicionado': (r) => r.body.includes(productName),
          });
        }
      }
      sleep(1);
    });
  }
}