// NOME DO ARQUIVO: k6-teastore/teste-carga-simples.js

import http from 'k6/http';
import { sleep, check } from 'k6';

// CORREÇÃO: Usar localhost:18081
const BASE_URL = 'http://localhost:18081/tools.descartes.teastore.webui';

export const options = {
  vus: 10,
  duration: '20s', // Mantendo a duração original do seu primeiro script
};

export default function () {
  const res = http.get(BASE_URL); // Acessa a URL corrigida
  check(res, {
    'Homepage OK': (r) => r.status === 200,
  });
  sleep(1);
}