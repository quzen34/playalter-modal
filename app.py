import modal

app = modal.App("playalter-test")

@app.function()
def hello():
    return "PLAYALTER Modal'da çalişiyor!"

@app.local_entrypoint()
def main():
    result = hello.remote()
    print(result)