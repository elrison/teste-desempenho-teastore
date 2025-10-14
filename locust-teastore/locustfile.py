from locust import HttpUser, task, between

class TeaStoreUser(HttpUser):
    # Define um tempo de espera aleatório entre 1 e 2 segundos
    # para simular o comportamento de um usuário real.
    wait_time = between(1, 2)

    # O endereço base da aplicação. O Locust usa 'self.client' para fazer requisições.
    # Não precisamos especificar o host aqui, faremos isso ao iniciar o teste.
    # No entanto, o caminho completo é importante.
    @task
    def load_home_page(self):
        self.client.get("/tools.descartes.teastore.webui/")