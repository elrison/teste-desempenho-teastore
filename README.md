# Análise Comparativa de Ferramentas de Teste de Desempenho com CI/CD

Este projeto realiza uma comparação prática entre três das mais populares ferramentas de teste de desempenho de código aberto: **k6**, **Locust** e **Apache JMeter**. O objetivo é avaliar não apenas a performance de cada ferramenta na geração de carga, mas também a sua maturidade para automação em um pipeline de CI/CD moderno utilizando **GitHub Actions**.

A aplicação alvo para os testes é o **TeaStore**, uma aplicação de e-commerce de referência baseada em microsserviços.

---

## 📊 Mix de Endpoints e Cenários de Teste

Os testes implementados simulam o comportamento real de usuários navegando na loja online TeaStore. Cada cenário segue um fluxo simplificado que representa as ações mais comuns de um cliente.

### Tabela 1. Mix de Endpoints Testados

| Mix | % | Endpoints TeaStore | Observações |
|-----|---|-------------------|-------------|
| A - Login | 20% | /login | Autenticação do usuário |
| B - Home | 20% | /home, /products | Página inicial e listagem de produtos |
| C - Categoria | 20% | /category?{id} | Navegação por categoria (link extraído dinamicamente) |
| D - Produto | 20% | /product?{id} | Visualização de produto específico (link extraído dinamicamente) |
| E - Logout | 20% | /loginAction?logout | Encerramento da sessão |

**Fluxo do Teste:** Login → Home → Categoria → Produto → Logout

**Características Técnicas:**
- Extração dinâmica de links para categorias e produtos (RegexExtractor no JMeter, BeautifulSoup no Locust, response.html() no k6)
- Cada usuário virtual executa o fluxo completo uma vez por iteração
- Medição de tempo de resposta, taxa de sucesso, throughput e detecção de erros

### Tabela 2. Cenários de Carga Implementados

| Cenário | Usuários Virtuais (VUs) | Duração | Ramp-up | Thresholds | Ferramentas |
|---------|-------------------------|---------|---------|------------|-------------|
| **Baixa Carga** | 100 | 2 minutos | 30s | p(95) < 500ms | k6, Locust, JMeter |
| **Média Carga** | 500 | 3 minutos | 60s | p(95) < 1s | k6, Locust, JMeter |
| **Alta Carga** | 1000 | 5 minutos | 90s | p(95) < 2s | k6, Locust, JMeter |

**Total de Testes:** 9 cenários (3 por ferramenta)
**Total de Relatórios HTML:** 15 (5 JMeter + 5 Locust + 5 k6)

---

## 🚀 Ferramentas e Tecnologias Utilizadas

| Tecnologia | Finalidade |
| :--- | :--- |
| **k6 (Grafana)** | Ferramenta de teste de carga moderna, focada em "testes como código" com scripts em JavaScript. |
| **Locust** | Ferramenta de teste de carga escrita em Python, conhecida por sua simplicidade e escalabilidade. |
| **Apache JMeter** | Ferramenta robusta e veterana para testes de carga e funcionais, baseada em Java. |
| **Docker** | Plataforma de contêineres para executar a aplicação e as ferramentas de teste em ambientes isolados. |
| **GitHub Actions** | Plataforma de CI/CD para automatizar a execução dos testes de desempenho a cada alteração no código. |

---

## ⚙️ O Processo de Configuração e Descoberta

A jornada para configurar este ambiente de testes automatizados foi um exercício prático de engenharia e depuração, seguindo os seguintes passos:

1.  **Configuração do Ambiente Local:**
    * Instalação e configuração do **Docker Desktop** como base para a execução de contêineres.
    * **Desafio:** A implantação da aplicação **TeaStore** provou ser o maior obstáculo inicial. Múltiplas tentativas baseadas em documentações desatualizadas falharam, incluindo:
        * Busca por arquivos `docker-compose.yml` que não existiam no código-fonte.
        * Tentativa de compilar o projeto Java do zero, o que exigiu a instalação de **JDK 17** e **Maven**.
    * **Solução:** A abordagem correta foi encontrada na documentação oficial do projeto (`GET_STARTED.md`), que indicava o uso de um arquivo `docker-compose.yaml` específico, localizado em `examples/docker/`.

2.  **Desenvolvimento dos Scripts de Teste:**
    * Criação de um cenário de **teste de carga simples** para as três ferramentas, simulando 10 usuários simultâneos acessando a página inicial do TeaStore por 30 segundos.
    * Os scripts foram desenvolvidos para serem executados via Docker, utilizando `host.docker.internal` para comunicação entre os contêineres de teste e o contêiner da aplicação.

3.  **Construção do Pipeline de CI/CD:**
    * Um workflow para **GitHub Actions** foi criado em `/.github/workflows/performance-tests.yml`.
    * O objetivo do pipeline é automatizar todo o processo: baixar o código, iniciar a aplicação TeaStore e executar os testes de k6, Locust e JMeter em sequência.

4.  **Depuração e Ajuste Fino do Pipeline:**
    * **Desafio 1: Gatilho da Branch:** O pipeline não era acionado porque o nome da branch local (`master`) não correspondia ao configurado no arquivo (`main`).
    * **Desafio 2: Comando `docker-compose`:** A versão do comando na máquina do GitHub Actions é `docker compose` (sem hífen), exigindo um ajuste no script.
    * **Desafio 3: Caminho do Arquivo:** O pipeline falhou ao não encontrar o arquivo de configuração do TeaStore, necessitando de uma correção precisa do caminho.
    * **Desafio 4: Artefatos do JMeter:** O JMeter se recusou a sobrescrever arquivos de relatório (`report/` e `results.jtl`), sendo necessário adicionar passos de limpeza (`rm -rf` e `rm -f`) antes da execução do teste.

---

## 🏁 Estado Atual

O projeto agora possui um pipeline de CI/CD totalmente funcional que, a cada `push` para a branch `master`, executa automaticamente os testes de desempenho com as três ferramentas e salva o relatório detalhado do JMeter como um artefato, que pode ser baixado para análise.

Este `README` serve como um registro do processo desafiador, mas bem-sucedido, de configuração de um ambiente de testes de performance automatizados.

---

## 📊 Resultados dos Testes de Desempenho

### Tabela 3. Latência e Performance por Ferramenta

| Ferramenta | Cenário | Média (ms) | P95 (ms) | P99 (ms)* | Throughput (req/s) | Taxa Erro | Iterações |
|------------|---------|------------|----------|-----------|-------------------|-----------|-----------|
| **K6** | 100 VUs | 419 | 1,270 | ~1,500 | 191.96 | 0.00% | 5,819 |
| **K6** | 500 VUs | 2,530 | 5,030 | ~5,800 | 186.90 | 0.00% | 5,862 |
| **K6** | 1000 VUs | 4,890 | 8,080 | ~9,500 | 194.99 | 0.00% | 6,303 |
| **JMeter** | 100 VUs | - | - | - | - | - | Pendente |
| **JMeter** | 500 VUs | - | - | - | - | - | Pendente |
| **JMeter** | 1000 VUs | - | - | - | - | - | Pendente |
| **Locust** | 100 VUs | - | - | - | - | - | Pendente |
| **Locust** | 500 VUs | - | - | - | - | - | Pendente |
| **Locust** | 1000 VUs | - | - | - | - | - | Pendente |

*P99 estimado com base na distribuição P90-P95

### Análise K6 - Resultados Obtidos

**✅ Taxa de Sucesso:**
- **100% de requisições bem-sucedidas** em todos os cenários
- 0 falhas em 179,840 requisições totais (58,190 + 58,620 + 63,030)
- Todas as validações (checks) passaram: login, home, categoria, produto, logout

**📈 Escalabilidade:**
- **Latência média:** 419ms (100 VUs) → 2,530ms (500 VUs) → 4,890ms (1000 VUs)
- **P95:** 1.27s (100 VUs) → 5.03s (500 VUs) → 8.08s (1000 VUs)
- Crescimento proporcional à carga aplicada

**⚡ Throughput:**
- **Estável entre 187-195 req/s** em todos os cenários
- Sistema mantém throughput consistente mesmo sob alta carga
- Limite de ~195 req/s sugere gargalo no SUT, não no gerador

**🔄 Duração dos Testes:**
- 100 VUs: 5m03s (303s)
- 500 VUs: 5m14s (314s)
- 1000 VUs: 5m23s (323s)

**💾 Tráfego de Rede:**
- Data recebida: 133-144 MB (~430-446 kB/s)
- Data enviada: 9.6-10 MB (~31-32 kB/s)

**Status:** ✅ K6 completo | ⏳ JMeter pendente | ⏳ Locust pendente
