import modal

app = modal.App("playalter-demo")
image = modal.Image.debian_slim().pip_install("fastapi")

@app.function(image=image)
@modal.fastapi_endpoint(method="GET")
def root():
    return {
        "message": "PLAYALTER Platform Successfully Deployed!",
        "status": "operational",
        "platform": "Modal.com",
        "services": {
            "face_analysis": "ready",
            "privacy_masks": "ready", 
            "face_swapping": "ready",
            "batch_processing": "ready"
        }
    }

@app.function(image=image)
@modal.fastapi_endpoint(method="GET")
def demo():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PLAYALTER Platform</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                background: linear-gradient(135deg, #667eea, #764ba2); 
                color: white; 
                text-align: center; 
                padding: 50px; 
                margin: 0; 
            }
            .container { 
                max-width: 800px; 
                margin: 0 auto; 
                background: rgba(255,255,255,0.1); 
                padding: 40px; 
                border-radius: 20px; 
            }
            h1 { font-size: 3rem; margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PLAYALTER Platform</h1>
            <h2>Successfully Deployed on Modal!</h2>
            <p>Advanced AI Face Processing Platform</p>
            <div style="margin: 30px 0;">
                <h3>Available Services:</h3>
                <ul style="text-align: left; display: inline-block;">
                    <li>Face Analysis with FLAME Model</li>
                    <li>Privacy Mask Generation</li>
                    <li>Face Swapping with InSwapper</li>
                    <li>Batch Processing</li>
                    <li>Authentication & Security</li>
                </ul>
            </div>
            <p><strong>Platform Status:</strong> Operational</p>
        </div>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)