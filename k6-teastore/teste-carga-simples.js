// NOME DO ARQUIVO: k6-teastore/teste-carga-simples.js

import http from 'k6/http';
import { sleep, check } from 'k6';

// Use environment variables to configure target host/port for CI reproducibility
const HOST = __ENV.HOST || 'http://localhost';
const PORT = __ENV.PORT || '18081';
const BASE_PATH = __ENV.BASE_PATH || '/tools.descartes.teastore.webui';
const BASE_UI = `${HOST}:${PORT}${BASE_PATH}`;

export const options = {
  vus: 10,
  duration: '20s', // Mantendo a duração original do seu primeiro script
};

export default function () {
  const res = http.get(BASE_UI);
  check(res, {
    'Homepage OK': (r) => r.status === 200,
  });
  sleep(1);
}