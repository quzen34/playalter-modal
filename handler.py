import modal

app = modal.App("playalter-beast")

@app.function(
    gpu="t4",
    image=modal.Image.debian_slim()
        .pip_install("opencv-python-headless", "pillow", "numpy")
)
def process_face_swap(source_image, target_image):
    return {"status": "test", "message": "PLAYALTER face swap ready"}

@app.local_entrypoint()
def test():
    result = process_face_swap.remote("test1", "test2")
    print(result)