"""Minimal test app to verify Cloud Run container starts correctly."""
import os
import gradio as gr

PORT = int(os.environ.get("PORT", 8080))

with gr.Blocks() as demo:
    gr.Markdown("# RetailPulse AI — Container is running! ✅")
    gr.Markdown(f"Port: {PORT}")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT)
