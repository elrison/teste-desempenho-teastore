import http from 'k6/http';
import { sleep, check } from 'k6';

// 1. Opções do Teste: Configura a carga que vamos gerar.
export const options = {
  vus: 10, // Simular 10 usuários virtuais (VUs) concorrentes
  duration: '30s', // Executar o teste por 30 segundos
};

// A URL alvo. Usamos 'host.docker.internal' para que o container Docker do k6
// consiga "enxergar" a aplicação que está rodando na sua máquina host (localhost).
const BASE_URL = 'http://host.docker.internal:8080/tools.descartes.teastore.webui/';

// 2. Cenário de Teste: O código que cada usuário virtual vai executar repetidamente.
export default function () {
  // Acessa a página inicial
  const res = http.get(BASE_URL);

  // Verifica se a página carregou com sucesso (status code 200)
  check(res, {
    'página inicial carregou com sucesso': (r) => r.status === 200,
  });

  // Pausa por 1 segundo para simular o tempo de "leitura" de um usuário real
  sleep(1);
}