import modal
import requests
import base64

app = modal.App.lookup("playalter-beast")
process_face_swap = app.process_face_swap

# Obama ve Trump örneği
source = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/President_Barack_Obama.jpg/256px-President_Barack_Obama.jpg"
target = "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/256px-Donald_Trump_official_portrait.jpg"

source_b64 = base64.b64encode(requests.get(source).content).decode()
target_b64 = base64.b64encode(requests.get(target).content).decode()

with modal.run():
    result = process_face_swap.remote(source_b64, target_b64)
    print(result)
    
    if result['status'] == 'success':
        with open("swap_result.jpg", "wb") as f:
            f.write(base64.b64decode(result['output']))
        print("✅ swap_result.jpg kaydedildi!")