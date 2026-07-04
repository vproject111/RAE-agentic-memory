from locust import HttpUser, between, task


class RAEUser(HttpUser):
    """
    Locust user class that simulates traffic to the RAE API.
    """

    wait_time = between(1, 2)  # Users wait 1-2 seconds between tasks

    @task
    def get_health(self):
        """
        Simulates a user requesting the /health endpoint.
        """
        self.client.get("/health")

    # Future tasks can be added here:
    # @task(3) # Higher weight means this task runs more often
    # def get_memory(self):
    #     self.client.get("/memory/123", name="/memory/[id]")
