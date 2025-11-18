import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE_URL = `${__ENV.HOST || 'http://localhost'}:${__ENV.PORT || '8080'}/tools.descartes.teastore.webui`;

export const options = {
  vus: 500,
  duration: '3m',
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% das requisições devem ser < 1s
    http_req_failed: ['rate<0.15'],    // Taxa de erro < 15%
  },
};

export default function () {
  group('Login', () => {
    const loginPage = http.get(`${BASE_URL}/login`);
    check(loginPage, { 'Login page loaded': (r) => r.status === 200 });

    const loginAction = http.post(`${BASE_URL}/loginAction`, {
      username: 'user1',
      password: 'password',
    });
    check(loginAction, { 'Login successful': (r) => r.status === 200 || r.status === 302 });
  });

  group('Navigate', () => {
    const homePage = http.get(`${BASE_URL}/`);
    check(homePage, { 'Home page loaded': (r) => r.status === 200 });

    const categoryPage = http.get(`${BASE_URL}/category`);
    check(categoryPage, { 'Category page loaded': (r) => r.status === 200 });

    const productPage = http.get(`${BASE_URL}/product`);
    check(productPage, { 'Product page loaded': (r) => r.status === 200 });
  });

  group('Logout', () => {
    const logoutAction = http.post(`${BASE_URL}/loginAction?logout=`);
    check(logoutAction, { 'Logout successful': (r) => r.status === 200 || r.status === 302 });
  });

  sleep(1);
}
