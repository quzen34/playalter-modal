import modal
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse

app = modal.App("playalter-working")

@app.function(image=modal.Image.debian_slim().pip_install("fastapi", "pillow"))
@modal.asgi_app()
def fastapi_app():
    web_app = FastAPI()
    
    @web_app.get("/")
    async def home():
        return HTMLResponse("""
        <html>
        <body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: Arial;">
            <h1>🎭 PLAYALTER Platform</h1>
            <h2>Services:</h2>
            <ul>
                <li>✅ Privacy Mask Generator</li>
                <li>✅ Face Swap</li>
                <li>✅ Style Transfer</li>
            </ul>
            <p>Upload interface coming soon...</p>
        </body>
        </html>
        """)
    
    return web_app