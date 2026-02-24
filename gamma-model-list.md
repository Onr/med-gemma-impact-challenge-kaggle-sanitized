look at https://huggingface.co/google/medgemma-27b-it for some examples
aslo the use cases are spesified here: https://developers.google.com/health-ai-developer-foundations/medgemma
fine tunn example https://colab.research.google.com/github/google-health/medgemma/blob/main/notebooks/fine_tune_with_hugging_face.ipynb


# Gamma Model List (MedGemma Impact Challenge)

This repo currently only documents the model families in `Kaggle competitions Med Gemma Impact challenge.md`.
Before locking in an approach, verify which specific checkpoints are enabled/allowed in the Kaggle competition environment.

## Models mentioned in our competition notes

### MedGemma (primary; use at least one)
- **MedGemma 4B (multimodal)**: medical text + image comprehension (lightweight option).
- **MedGemma 27B (text-only)**: medical text comprehension/reasoning (largest text model).
- **MedGemma 27B (multimodal)**: medical text + image comprehension (largest multimodal model).

### Other HAI-DEF model families (use if the competition allows auxiliary models)
- **MedASR**: medical speech-to-text (dictation/transcription) to feed into MedGemma.
- **MedSigLIP**: medically optimized image encoder used inside MedGemma (the notes link to `google/medgemma-27b-it` as an example page).
- **CXR Foundation**: chest X-ray embedding model (retrieval, classification, semantic search).
- **Derm Foundation**: dermatology image embedding model (classification, image quality).
- **Path Foundation**: histopathology image model (tissue classification, grading, similar-image search).
- **HeAR (Lung Acoustics)**: non-speech audio embedding model for lung sounds.

## Recommendation for “use at least one”
- Start with **MedGemma 4B multimodal** if you need images and have tighter compute constraints.
- Start with **MedGemma 27B text-only** if your solution is primarily text (guidelines/notes/QA).
