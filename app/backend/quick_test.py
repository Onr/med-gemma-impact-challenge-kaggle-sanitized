"""
Quick MedGemma Test - Minimal Example

This is the simplest possible test to verify MedGemma works locally.
Run this first before testing the full workflow.

Usage:
    python quick_test.py                          # Uses mock model
    python quick_test.py --model google/medgemma-1.5-4b-it  # Real model
"""

import os
import sys

from model_resolver import resolve_model_id

def test_with_mock():
    """Test with simulated responses (no GPU needed)."""
    print("🧪 Testing with MOCK model...\n")
    
    # Simulate a simple exchange
    test_input = "I have a patient with chronic back pain, what treatment options should I consider?"
    
    mock_response = """Based on your query about chronic back pain, here's my analysis:

**Assessment:**
The patient presents with chronic low back pain. Key considerations include:
- Duration and severity of symptoms
- Previous treatments attempted
- Functional limitations

**Evidence-Based Options:**
1. **Physical Therapy** - Strong evidence (Grade A)
2. **Exercise Programs** - Moderate evidence (Grade B)  
3. **NSAIDs** - Short-term relief (Grade A)
4. **CBT for Pain** - Moderate evidence for chronic pain

**Recommendation:**
Start with physical therapy combined with structured exercise.
Would you like me to help formulate a specific PICO question?"""

    print(f"📝 Input: {test_input}\n")
    print(f"🤖 Response:\n{mock_response}")
    print("\n✅ Mock test passed!")
    return True


def test_with_real_model(model_id: str):
    """Test with actual MedGemma model."""
    resolved_id = resolve_model_id(model_id)
    if resolved_id != model_id:
        print(f"Resolved model_id '{model_id}' -> '{resolved_id}'")
    model_id = resolved_id
    print(f"🔄 Loading model: {model_id}")
    
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        print("❌ Missing dependencies. Run:")
        print("   pip install torch transformers accelerate")
        return False
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    
    print(f"   Device: {device}, dtype: {dtype}")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map="auto" if device == "cuda" else None,
            torch_dtype=dtype if device == "cuda" else None,
        )
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        print("\n💡 Common issues:")
        print("   1. Set HF_TOKEN for gated models: export HF_TOKEN=...")
        print("   2. Check model ID is correct")
        print("   3. Ensure sufficient GPU memory")
        return False
    
    print("✅ Model loaded!")
    
    # Simple test
    prompt = "You are a medical assistant. Briefly explain what PICO stands for in evidence-based medicine."
    
    print(f"\n📝 Test prompt: {prompt}")
    
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            do_sample=True,
            temperature=0.7
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Remove the prompt from response
    if prompt in response:
        response = response.replace(prompt, "").strip()
    
    print(f"\n🤖 Response:\n{response}")
    print("\n✅ Real model test passed!")
    return True


def check_environment():
    """Check if environment is set up correctly."""
    print("🔍 Checking environment...\n")
    
    checks = []
    
    # Python version
    py_ver = sys.version_info
    checks.append(("Python 3.8+", py_ver >= (3, 8)))
    
    # PyTorch
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        checks.append(("PyTorch installed", True))
        checks.append(("CUDA available", cuda_available))
        if cuda_available:
            checks.append((f"GPU: {torch.cuda.get_device_name(0)}", True))
    except ImportError:
        checks.append(("PyTorch installed", False))
    
    # Transformers
    try:
        import transformers
        checks.append((f"Transformers {transformers.__version__}", True))
    except ImportError:
        checks.append(("Transformers installed", False))
    
    # HF Token
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_HUB_TOKEN")
    checks.append(("HF_TOKEN set", bool(hf_token)))
    
    # Print results
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    print()
    return all(passed for _, passed in checks if "CUDA" not in _[0])


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--check", action="store_true", help="Only check environment")
    args = parser.parse_args()
    
    print("\n" + "="*50)
    print("🏥 MEDGEMMA QUICK TEST")
    print("="*50 + "\n")
    
    if args.check:
        check_environment()
    elif args.model:
        check_environment()
        test_with_real_model(args.model)
    else:
        # Run mock test by default
        test_with_mock()
        print("\n" + "-"*50)
        print("💡 To test with a real model:")
        print("   python quick_test.py --model google/medgemma-1.5-4b-it")
        print("\n💡 To check your environment:")
        print("   python quick_test.py --check")
