class Env:
    def __init__(self, env_path: str):
        self.env_path = env_path
        self.file_name = self.env_path.split("/")[-1]
        self.name = (
            "env" if self.file_name == ".env" else self.file_name.removeprefix(".env.")
        )

    def __str__(self) -> str:
        return self.name
