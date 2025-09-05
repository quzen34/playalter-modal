import modal

app = modal.App("final-test")

@app.function(image=modal.Image.debian_slim().pip_install("fastapi"))
@modal.web_endpoint(method="GET")
def web_function():
    import datetime
    return {
        "message": "PLAYALTER is working!", 
        "time": str(datetime.datetime.now()),
        "status": "SUCCESS"
    }