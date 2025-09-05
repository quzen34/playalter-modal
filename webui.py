"""
PLAYALTER Web Interface
Simple Gradio UI for face swapping
"""

import modal
import gradio as gr
import base64
from PIL import Image
import io

# Connect to Modal app
app = modal.App.lookup("playalter-beast")
swap_function = app.process_face_swap

def swap_faces(source_image, target_image):
    """Process face swap via Modal"""
    if source_image is None or target_image is None:
        return None, "Please upload both images"
    
    try:
        # Convert to base64
        source_buffer = io.BytesIO()
        source_image.save(source_buffer, format='JPEG')
        source_b64 = base64.b64encode(source_buffer.getvalue()).decode()
        
        target_buffer = io.BytesIO()
        target_image.save(target_buffer, format='JPEG')
        target_b64 = base64.b64encode(target_buffer.getvalue()).decode()
        
        # Call Modal function
        with modal.run():
            result = swap_function.remote(source_b64, target_b64)
        
        if result["success"]:
            # Decode result
            output_data = base64.b64decode(result['output'])
            output_image = Image.open(io.BytesIO(output_data))
            return output_image, result['message']
        else:
            return None, result['message']
            
    except Exception as e:
        return None, f"Error: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="PLAYALTER Face Swap") as demo:
    gr.Markdown("""
    # 🎭 PLAYALTER™ Face Swap
    ### Powered by Modal.com - Fast & Secure Face Swapping
    """)
    
    with gr.Row():
        with gr.Column():
            source_img = gr.Image(label="Source Face", type="pil")
        with gr.Column():
            target_img = gr.Image(label="Target Face", type="pil")
    
    swap_btn = gr.Button("🔄 Swap Faces", variant="primary", size="lg")
    
    with gr.Row():
        output_img = gr.Image(label="Result")
    
    status = gr.Textbox(label="Status")
    
    swap_btn.click(
        fn=swap_faces,
        inputs=[source_img, target_img],
        outputs=[output_img, status]
    )
    
    gr.Examples(
        examples=[
            ["examples/obama.jpg", "examples/biden.jpg"],
            ["examples/person1.jpg", "examples/person2.jpg"]
        ],
        inputs=[source_img, target_img]
    )

if __name__ == "__main__":
    # First install gradio if not installed
    import subprocess
    subprocess.run(["pip", "install", "gradio", "modal"], check=False)
    
    print("🌐 Starting PLAYALTER Web UI...")
    demo.launch(share=True, server_port=7860)