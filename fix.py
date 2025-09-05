import modal

app = modal.App("test-fix")

@app.function(
    image=modal.Image.debian_slim().pip_install("fastapi"),
    cpu=1
)
@modal.web_endpoint()
def hello():
    return {"message": "PLAYALTER Working!"}