from locust import HttpUser, task, between

class TeaStoreUser(HttpUser):

    wait_time = between(1, 2)

    @task
    def load_home_page(self):
        # Request relative to host (host set by CI to include base path)
        self.client.get("/home", name="/home")
