# Análise Comparativa de Ferramentas de Teste de Desempenho com CI/CD

Este projeto realiza uma comparação prática entre três das mais populares ferramentas de teste de desempenho de código aberto: **k6**, **Locust** e **Apache JMeter**. O objetivo é avaliar não apenas a performance de cada ferramenta na geração de carga, mas também a sua maturidade para automação em um pipeline de CI/CD moderno utilizando **GitHub Actions**.

A aplicação alvo para os testes é o **TeaStore**, uma aplicação de e-commerce de referência baseada em microsserviços.

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
