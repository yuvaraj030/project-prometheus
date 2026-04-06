class SandboxAgent:
    def __init__(self):
        self.version = 1.0
        self.capabilities = ["basic_logic"]
    
    def process(self, data):
        return f"Processed {data} with version {self.version}"