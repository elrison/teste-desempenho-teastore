import http from 'k6/http';
import { sleep, check } from 'k6';

const BASE_URL = 'http://localhost:18081/tools.descartes.teastore.webui';

export const options = {
  vus: 10,
  duration: '20s',
};

export default function () {
  const res = http.get(BASE_URL);
  check(res, {
    'Homepage OK': (r) => r.status === 200,
  });
  sleep(1);
}
