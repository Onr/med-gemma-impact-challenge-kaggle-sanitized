"""
MedGemma Local-Only Test Script

This script tests the MedGemma workflow without any frontend or cloud API.
It simulates a user conversation through the EBP (Evidence-Based Practice) phases.

Usage:
    # Set your HuggingFace token for gated models (optional if using local paths)
    export HF_TOKEN=your_token
    
    # Run the test
    python test_medgemma_local.py
    
    # Or specify a local model path
    python test_medgemma_local.py --model /kaggle/input/medgemma-4b-it
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from model_resolver import resolve_model_id

# ============================================================================
# Configuration
# ============================================================================

class Phase(Enum):
    ASK = "ASK"
    ACQUIRE = "ACQUIRE"
    APPRAISE = "APPRAISE"
    APPLY = "APPLY"
    ASSESS = "ASSESS"

class Role(Enum):
    PHYSICIAN = "Physician"
    PT = "Physical Therapist"
    OT = "Occupational Therapist"
    NURSE = "Nurse"
    PHARMACIST = "Pharmacist"

@dataclass
class ConversationState:
    """Tracks conversation state across the EBP workflow."""
    phase: Phase = Phase.ASK
    role: Role = Role.PHYSICIAN
    patient_context: str = ""
    pico: Dict[str, str] = field(default_factory=lambda: {
        "patient": "",
        "intervention": "",
        "comparison": "",
        "outcome": ""
    })
    history: List[Dict[str, str]] = field(default_factory=list)


# ============================================================================
# System Prompts (same as frontend)
# ============================================================================

def get_system_prompt(role: Role, phase: Phase, patient_context: str) -> str:
    return f"""
You are MedGemma, an expert EBP Copilot.
Current User Role: {role.value}
Current Phase: {phase.value}
Patient Context: {patient_context or "None provided yet"}

CORE OBJECTIVE:
Guide the user through the Evidence-Based Practice (EBP) cycle. Be concise, clinical, and helpful.

ROLE BEHAVIOR:
- Physician: Focus on diagnosis, pharmacology, prognosis. Use technical terms.
- PT: Focus on functional outcomes, movement, rehab protocols.
- OT: Focus on ADLs, participation, environmental adaptation.
- Nurse: Focus on holistic care, symptom management, education.
- Pharmacist: Focus on interactions, dosing, PK/PD.

PHASE INSTRUCTIONS:
- ASK: Extract PICO (Patient, Intervention, Comparison, Outcome). Ask for missing parts.
- ACQUIRE: Generate 3-5 plausible, high-quality simulated references (RCTs, Meta-analyses).
- APPRAISE: Extract key appraisal points (Strengths, Weaknesses, Bias risks).
- APPLY: Synthesize evidence into concrete clinical actions.
- ASSESS: Define specific outcome measures, targets, and monitoring frequencies.

Keep responses focused and clinically relevant.
"""


# ============================================================================
# Model Loading
# ============================================================================

class MedGemmaModel:
    """Wrapper for MedGemma model inference."""
    
    def __init__(self, model_id: str, device: str = "auto"):
        self.model_id = model_id
        self.device = device
        self.model = None
        self.processor = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load model and processor/tokenizer."""
        print(f"🔄 Loading model: {self.model_id}")
        print(f"   This may take a few minutes for large models...")
        
        try:
            import torch
            from transformers import AutoTokenizer, AutoProcessor
        except ImportError:
            print("❌ Missing dependencies. Install with:")
            print("   pip install torch transformers accelerate")
            sys.exit(1)
        
        # Determine device and dtype
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.device == "cuda":
            if torch.cuda.is_bf16_supported():
                self.dtype = torch.bfloat16
            else:
                self.dtype = torch.float16
        else:
            self.dtype = torch.float32
        
        print(f"   Device: {self.device}, dtype: {self.dtype}")
        
        # Check if multimodal
        is_multimodal = any(kw in self.model_id.lower() for kw in ['4b', 'mm', 'vision', 'multimodal'])
        
        # Load model
        if is_multimodal:
            # Try multimodal model classes
            for cls_name in ['AutoModelForImageTextToText', 'AutoModelForVision2Seq', 'AutoModelForCausalLM']:
                try:
                    from transformers import AutoModelForCausalLM
                    ModelClass = getattr(__import__('transformers', fromlist=[cls_name]), cls_name)
                    break
                except (AttributeError, ImportError):
                    continue
            else:
                from transformers import AutoModelForCausalLM
                ModelClass = AutoModelForCausalLM
            
            try:
                self.processor = AutoProcessor.from_pretrained(self.model_id)
            except Exception:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        else:
            from transformers import AutoModelForCausalLM
            ModelClass = AutoModelForCausalLM
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        
        self.model = ModelClass.from_pretrained(
            self.model_id,
            device_map="auto" if self.device == "cuda" else None,
            torch_dtype=self.dtype if self.device == "cuda" else None,
        )
        
        print(f"✅ Model loaded successfully!")
    
    def generate(self, prompt: str, system_prompt: str = "", max_new_tokens: int = 512) -> str:
        """Generate text response."""
        import torch
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAssistant:"
        
        # Use processor or tokenizer
        if self.processor:
            inputs = self.processor(text=full_prompt, return_tensors="pt")
        else:
            inputs = self.tokenizer(full_prompt, return_tensors="pt")
        
        # Move to device
        inputs = {k: v.to(self.model.device) if hasattr(v, 'to') else v for k, v in inputs.items()}
        
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                pad_token_id=self.tokenizer.eos_token_id if self.tokenizer else None
            )
        
        # Decode
        if self.processor and hasattr(self.processor, 'batch_decode'):
            text = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]
        else:
            text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response
        if "Assistant:" in text:
            text = text.split("Assistant:")[-1].strip()
        
        return text


# ============================================================================
# Mock Model (for testing without GPU)
# ============================================================================

class MockMedGemmaModel:
    """Mock model for testing the workflow without actual model inference."""
    
    def __init__(self, model_id: str = "mock"):
        self.model_id = model_id
        print(f"🧪 Using MOCK model (no actual inference)")
        print(f"   This simulates responses for workflow testing.")
    
    def generate(self, prompt: str, system_prompt: str = "", max_new_tokens: int = 512) -> str:
        """Generate simulated response based on phase."""
        prompt_lower = prompt.lower()
        
        # Detect phase from system prompt - look for "Current Phase: X"
        if "Current Phase: ASSESS" in system_prompt:
            return self._assess_phase_response(prompt)
        elif "Current Phase: APPLY" in system_prompt:
            return self._apply_phase_response(prompt)
        elif "Current Phase: APPRAISE" in system_prompt:
            return self._appraise_phase_response(prompt)
        elif "Current Phase: ACQUIRE" in system_prompt:
            return self._acquire_phase_response(prompt)
        else:
            return self._ask_phase_response(prompt)
    
    def _ask_phase_response(self, prompt: str) -> str:
        return """Based on your case, I'm formulating a PICO question:

**P (Patient):** Adult patient with the described condition
**I (Intervention):** The treatment approach you're considering  
**C (Comparison):** Standard care or alternative treatment
**O (Outcome):** Clinical improvement, functional outcomes

Could you provide more details about:
1. The specific patient population (age, comorbidities)?
2. What intervention you're considering?
3. What outcome measures matter most?"""

    def _acquire_phase_response(self, prompt: str) -> str:
        return """I found the following relevant evidence:

**1. Smith et al. (2024)** - NEJM
   - RCT, n=450, High relevance
   - Multicenter trial showing significant benefit

**2. Johnson & Lee (2023)** - Lancet  
   - Systematic Review, 12 studies, High relevance
   - Meta-analysis supporting intervention efficacy

**3. Williams et al. (2023)** - JAMA
   - Cohort Study, n=1200, Medium relevance
   - Real-world outcomes data

Would you like me to appraise these studies for methodological quality?"""

    def _appraise_phase_response(self, prompt: str) -> str:
        return """Critical appraisal of the evidence:

**Strengths:**
✅ Adequate sample sizes across studies
✅ Consistent effect direction
✅ Low heterogeneity in meta-analysis (I²=25%)

**Weaknesses:**
⚠️ Limited long-term follow-up (max 12 months)
⚠️ Industry funding in primary RCT
⚠️ Single-blinded design due to intervention nature

**Risk of Bias:** Moderate - primarily due to blinding limitations

**Overall:** Evidence supports intervention with moderate confidence."""

    def _apply_phase_response(self, prompt: str) -> str:
        return """Based on the evidence, here are clinical recommendations:

**Actions:**
1. **Initiate treatment** - Evidence supports starting intervention
2. **Monitor closely** - Weekly assessments for first month
3. **Patient education** - Discuss expected outcomes and timeline
4. **Document** - Track response for future reference

**Considerations:**
- Individual patient factors may modify response
- Consider contraindications
- Shared decision-making with patient

Ready to establish outcome measures?"""

    def _assess_phase_response(self, prompt: str) -> str:
        return """Outcome assessment plan:

**Primary Outcomes:**
| Metric | Target | Frequency |
|--------|--------|-----------|
| Pain Score (VAS) | <3/10 | Weekly |
| Function Scale | >80% | Bi-weekly |
| Quality of Life | Improved | Monthly |

**Secondary Outcomes:**
- Medication use reduction
- Return to activities
- Patient satisfaction

**Review Points:**
- 4 weeks: Initial response assessment
- 12 weeks: Treatment continuation decision
- 6 months: Long-term outcome evaluation

This completes the EBP cycle. Would you like to start a new case?"""


# ============================================================================
# Conversation Runner
# ============================================================================

class EBPConversation:
    """Manages the EBP conversation flow."""
    
    def __init__(self, model, state: Optional[ConversationState] = None):
        self.model = model
        self.state = state or ConversationState()
    
    def send_message(self, user_message: str) -> str:
        """Send a message and get response."""
        # Get system prompt
        system_prompt = get_system_prompt(
            self.state.role,
            self.state.phase,
            self.state.patient_context
        )
        
        # Generate response
        response = self.model.generate(
            prompt=user_message,
            system_prompt=system_prompt,
            max_new_tokens=512
        )
        
        # Update history
        self.state.history.append({"role": "user", "content": user_message})
        self.state.history.append({"role": "assistant", "content": response})
        
        return response
    
    def advance_phase(self):
        """Move to next EBP phase."""
        phases = list(Phase)
        current_idx = phases.index(self.state.phase)
        if current_idx < len(phases) - 1:
            self.state.phase = phases[current_idx + 1]
            print(f"\n📍 Advanced to {self.state.phase.value} phase\n")
    
    def set_role(self, role: Role):
        """Change user role."""
        self.state.role = role
        print(f"👤 Role set to: {role.value}")
    
    def set_patient_context(self, context: str):
        """Set patient context."""
        self.state.patient_context = context


# ============================================================================
# Test Scenarios
# ============================================================================

def run_automated_test(model):
    """Run automated test through all EBP phases."""
    print("\n" + "="*60)
    print("🧪 AUTOMATED EBP WORKFLOW TEST")
    print("="*60)
    
    conv = EBPConversation(model)
    
    # Test messages for each phase
    test_cases = [
        # ASK phase
        ("I have a 65-year-old patient with chronic low back pain for 6 months. "
         "They've tried NSAIDs with limited relief. Considering physical therapy. "
         "What's the best approach?"),
        
        # ACQUIRE phase (after advancing)
        ("Please find evidence on physical therapy for chronic low back pain in elderly patients."),
        
        # APPRAISE phase
        ("Can you critically appraise the quality of these studies?"),
        
        # APPLY phase
        ("Based on this evidence, what specific interventions should I recommend?"),
        
        # ASSESS phase
        ("What outcomes should I track to measure treatment success?"),
    ]
    
    for i, message in enumerate(test_cases):
        print(f"\n{'─'*50}")
        print(f"📍 Phase: {conv.state.phase.value}")
        print(f"{'─'*50}")
        print(f"\n👤 USER: {message[:100]}..." if len(message) > 100 else f"\n👤 USER: {message}")
        
        response = conv.send_message(message)
        print(f"\n🤖 MEDGEMMA:\n{response}")
        
        # Advance phase (except for last message)
        if i < len(test_cases) - 1:
            conv.advance_phase()
    
    print("\n" + "="*60)
    print("✅ AUTOMATED TEST COMPLETE")
    print("="*60)
    
    return conv


def run_interactive_mode(model):
    """Run interactive conversation mode."""
    print("\n" + "="*60)
    print("💬 INTERACTIVE MODE")
    print("="*60)
    print("\nCommands:")
    print("  /next     - Advance to next EBP phase")
    print("  /phase    - Show current phase")
    print("  /role X   - Set role (physician, pt, ot, nurse, pharmacist)")
    print("  /reset    - Reset conversation")
    print("  /quit     - Exit")
    print("="*60)
    
    conv = EBPConversation(model)
    
    while True:
        try:
            user_input = input(f"\n[{conv.state.phase.value}] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Handle commands
        if user_input.startswith("/"):
            cmd = user_input.lower().split()
            if cmd[0] == "/quit":
                print("Goodbye!")
                break
            elif cmd[0] == "/next":
                conv.advance_phase()
            elif cmd[0] == "/phase":
                print(f"Current phase: {conv.state.phase.value}")
            elif cmd[0] == "/role" and len(cmd) > 1:
                role_map = {
                    "physician": Role.PHYSICIAN,
                    "pt": Role.PT,
                    "ot": Role.OT,
                    "nurse": Role.NURSE,
                    "pharmacist": Role.PHARMACIST
                }
                if cmd[1] in role_map:
                    conv.set_role(role_map[cmd[1]])
                else:
                    print(f"Unknown role. Options: {list(role_map.keys())}")
            elif cmd[0] == "/reset":
                conv = EBPConversation(model)
                print("Conversation reset.")
            else:
                print(f"Unknown command: {cmd[0]}")
            continue
        
        # Send message
        response = conv.send_message(user_input)
        print(f"\n🤖 MedGemma: {response}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test MedGemma locally")
    parser.add_argument("--model", type=str, default=None,
                        help="Model ID or path (e.g., google/medgemma-1.5-4b-it or /kaggle/input/...)")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock model (no GPU needed, simulated responses)")
    parser.add_argument("--interactive", action="store_true",
                        help="Run in interactive mode instead of automated test")
    parser.add_argument("--device", type=str, default="auto",
                        help="Device: auto, cuda, cpu")
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🏥 MEDGEMMA LOCAL TEST")
    print("="*60)
    
    # Load model
    if args.mock:
        model = MockMedGemmaModel()
    else:
        model_id = args.model or os.getenv("MEDGEMMA_MODEL_ID", "google/medgemma-1.5-4b-it")
        resolved_id = resolve_model_id(model_id)
        if resolved_id != model_id:
            print(f"Resolved model_id '{model_id}' -> '{resolved_id}'")
        model_id = resolved_id
        
        # Check for HF token
        if not os.getenv("HF_TOKEN") and not os.getenv("HUGGINGFACE_HUB_TOKEN"):
            print("\n⚠️  No HF_TOKEN found. If using gated models, set:")
            print("   export HF_TOKEN=your_huggingface_token")
        
        try:
            model = MedGemmaModel(model_id, device=args.device)
        except Exception as e:
            print(f"\n❌ Failed to load model: {e}")
            print("\n💡 Try running with --mock to test the workflow without a model:")
            print("   python test_medgemma_local.py --mock")
            sys.exit(1)
    
    # Run test
    if args.interactive:
        run_interactive_mode(model)
    else:
        run_automated_test(model)


if __name__ == "__main__":
    main()
