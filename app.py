import modal

app = modal.App("playalter-test")

@app.function()
def hello():
    return "PLAYALTER Modal'da çalışıyor!"

@app.local_entrypoint()
def main():
    result = hello.remote()
    print(result)