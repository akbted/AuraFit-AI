import torch

def get_device():
    """Detect the best available device for inference."""
    if torch.cuda.is_available():
        device = "cuda"
        print(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
    elif torch.backends.mps.is_available():
        device = "mps"
        print("Using Apple Silicon GPU (MPS)")
    else:
        device = "cpu"
        print("Using CPU (slower inference)")
    
    return device

# Cache the device on import
DEVICE = get_device()