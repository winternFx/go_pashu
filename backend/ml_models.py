import os
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import torch
from torch import Tensor

try:
    from PIL import Image
    from torchvision import transforms as T
except ImportError:  # pragma: no cover - handled at runtime
    Image = None  # type: ignore
    T = None  # type: ignore

try:
    import torchaudio
except ImportError:  # pragma: no cover - handled at runtime
    torchaudio = None  # type: ignore


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_torch_model(path: str) -> Optional[torch.nn.Module]:
    """
    Load a Torch/ TorchScript model from disk.

    This is intentionally generic so you can drop in your own
    trained models without changing application code.
    """
    if not os.path.exists(path):
        return None

    try:
        # Prefer TorchScript if available
        model = torch.jit.load(path, map_location=device)
    except Exception:
        # Fallback to regular pickled nn.Module
        model = torch.load(path, map_location=device)

    if isinstance(model, torch.nn.Module):
        model.to(device)
        model.eval()
        return model

    return None


@lru_cache(maxsize=1)
def _get_image_transform() -> Optional[Any]:
    if T is None:
        return None
    return T.Compose(
        [
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


def _load_image_tensor(image_path: str) -> Optional[Tensor]:
    if Image is None or T is None:
        return None

    if not os.path.exists(image_path):
        return None

    transform = _get_image_transform()
    if transform is None:
        return None

    try:
        image = Image.open(image_path).convert("RGB")
        tensor = transform(image).unsqueeze(0)  # (1, C, H, W)
        return tensor.to(device)
    except Exception:
        return None


def _softmax_logits(logits: Tensor) -> Tensor:
    if logits.ndim == 1:
        logits = logits.unsqueeze(0)
    return torch.softmax(logits, dim=1)


@lru_cache(maxsize=1)
def _get_fmd_model() -> Optional[torch.nn.Module]:
    """
    Foot-and-mouth disease classifier model.

    Expects a binary classifier where output[0, 1] is
    the probability/logit for 'Foot and Mouth Disease'.
    """
    model_path = os.getenv("FMD_MODEL_PATH", "models/fmd_model.pt")
    return _load_torch_model(model_path)


def predict_foot_mouth_disease(image_path: str) -> Dict[str, Any]:
    """
    Run Foot and Mouth disease detection on an image.

    Returns a JSON-serializable dictionary.
    """
    model = _get_fmd_model()
    if model is None:
        return {
            "model_configured": False,
            "disease": "Foot and Mouth Disease",
            "probability": 0.0,
            "has_disease": False,
            "message": (
                "Foot and Mouth Disease model is not configured. "
                "Place a trained Torch/TorchScript model at FMD_MODEL_PATH."
            ),
        }

    tensor = _load_image_tensor(image_path)
    if tensor is None:
        return {
            "model_configured": True,
            "disease": "Foot and Mouth Disease",
            "probability": 0.0,
            "has_disease": False,
            "message": "Unable to load image for inference.",
        }

    with torch.no_grad():
        outputs = model(tensor)
        probs = _softmax_logits(outputs)
        # Assume index 1 corresponds to 'disease present'
        prob = float(probs[0, 1].item()) if probs.shape[1] > 1 else float(probs[0, 0].item())

    has_disease = prob >= 0.5

    if has_disease:
        message = (
            "Signs of Foot and Mouth Disease detected in this image. "
            "Please isolate the animal and consult a veterinarian immediately."
        )
    else:
        message = (
            "No strong visual signs of Foot and Mouth Disease detected. "
            "Continue to monitor the animal and confirm with a veterinarian if symptoms appear."
        )

    return {
        "model_configured": True,
        "disease": "Foot and Mouth Disease",
        "probability": prob,
        "has_disease": has_disease,
        "message": message,
    }


def _cosine_similarity(a: Tensor, b: Tensor) -> float:
    a = a / (a.norm(dim=-1, keepdim=True) + 1e-8)
    b = b / (b.norm(dim=-1, keepdim=True) + 1e-8)
    return float(torch.sum(a * b).item())


@lru_cache(maxsize=1)
def _get_face_model() -> Optional[torch.nn.Module]:
    """
    Cow face embedding model.

    This model should take a preprocessed image tensor (1, C, H, W)
    and return a 1D embedding tensor.
    """
    model_path = os.getenv("COW_FACE_MODEL_PATH", "models/cow_face_model.pt")
    return _load_torch_model(model_path)


def identify_cow_by_face(
    query_image_path: str,
    known_animals: List[Dict[str, Any]],
    similarity_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Identify a cow by comparing its face against known animal images.

    known_animals: list of dicts with at least:
      - id
      - animal_name
      - image_path
    """
    model = _get_face_model()
    if model is None:
        return {
            "model_configured": False,
            "match_found": False,
            "message": (
                "Cow face identification model is not configured. "
                "Place a trained Torch/TorchScript model at COW_FACE_MODEL_PATH."
            ),
        }

    query_tensor = _load_image_tensor(query_image_path)
    if query_tensor is None:
        return {
            "model_configured": True,
            "match_found": False,
            "message": "Unable to load query image for inference.",
        }

    if not known_animals:
        return {
            "model_configured": True,
            "match_found": False,
            "message": "No reference animal images available for identification.",
        }

    with torch.no_grad():
        query_emb = model(query_tensor)
        if query_emb.ndim > 1:
            query_emb = query_emb.squeeze(0)

    best_score: float = -1.0
    best_animal: Optional[Dict[str, Any]] = None

    for animal in known_animals:
        image_path = animal.get("image_path")
        if not image_path:
            continue

        ref_tensor = _load_image_tensor(image_path)
        if ref_tensor is None:
            continue

        with torch.no_grad():
            ref_emb = model(ref_tensor)
            if ref_emb.ndim > 1:
                ref_emb = ref_emb.squeeze(0)

        score = _cosine_similarity(query_emb, ref_emb)
        if score > best_score:
            best_score = score
            best_animal = animal

    if best_animal is None or best_score < similarity_threshold:
        return {
            "model_configured": True,
            "match_found": False,
            "similarity": best_score if best_score >= 0 else 0.0,
            "message": "No confident match found for this cow's face.",
        }

    return {
        "model_configured": True,
        "match_found": True,
        "similarity": best_score,
        "animal": {
            "id": best_animal.get("id"),
            "animal_name": best_animal.get("animal_name"),
            "breed": best_animal.get("breed"),
            "tag_id": best_animal.get("tag_id"),
            "image_path": best_animal.get("image_path"),
        },
        "message": (
            f"Identified cow '{best_animal.get('animal_name')}' "
            f"with similarity score {best_score:.2f}."
        ),
    }


@lru_cache(maxsize=1)
def _get_voice_model() -> Optional[torch.nn.Module]:
    """
    Cow voice embedding / classifier model.

    This model should take a mel-spectrogram tensor and return
    a 1D embedding tensor.
    """
    model_path = os.getenv("COW_VOICE_MODEL_PATH", "models/cow_voice_model.pt")
    return _load_torch_model(model_path)


def _load_audio_tensor(audio_path: str, target_sample_rate: int = 16000) -> Optional[Tensor]:
    if torchaudio is None:
        return None

    if not os.path.exists(audio_path):
        return None

    try:
        waveform, sample_rate = torchaudio.load(audio_path)
        # Convert to mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        if sample_rate != target_sample_rate:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=target_sample_rate,
            )
            waveform = resampler(waveform)

        # Generate mel-spectrogram
        mel_spec_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=target_sample_rate,
            n_mels=64,
        )
        mel_spec = mel_spec_transform(waveform)  # (1, n_mels, time)
        # Log amplitude
        mel_spec = torch.log(mel_spec + 1e-6)
        return mel_spec.to(device)
    except Exception:
        return None


def identify_cow_by_voice(
    query_audio_path: str,
    known_animals: List[Dict[str, Any]],
    similarity_threshold: float = 0.7,
) -> Dict[str, Any]:
    """
    Identify a cow by comparing its voice against known animal audio clips.

    known_animals: list of dicts with at least:
      - id
      - animal_name
      - audio_path
    """
    model = _get_voice_model()
    if model is None:
        return {
            "model_configured": False,
            "match_found": False,
            "message": (
                "Cow voice identification model is not configured. "
                "Place a trained Torch/TorchScript model at COW_VOICE_MODEL_PATH."
            ),
        }

    query_tensor = _load_audio_tensor(query_audio_path)
    if query_tensor is None:
        return {
            "model_configured": True,
            "match_found": False,
            "message": "Unable to load query audio for inference.",
        }

    if not known_animals:
        return {
            "model_configured": True,
            "match_found": False,
            "message": "No reference animal audio samples available for identification.",
        }

    with torch.no_grad():
        query_emb = model(query_tensor)
        if query_emb.ndim > 1:
            query_emb = query_emb.squeeze(0)

    best_score: float = -1.0
    best_animal: Optional[Dict[str, Any]] = None

    for animal in known_animals:
        audio_path = animal.get("audio_path")
        if not audio_path:
            continue

        ref_tensor = _load_audio_tensor(audio_path)
        if ref_tensor is None:
            continue

        with torch.no_grad():
            ref_emb = model(ref_tensor)
            if ref_emb.ndim > 1:
                ref_emb = ref_emb.squeeze(0)

        score = _cosine_similarity(query_emb, ref_emb)
        if score > best_score:
            best_score = score
            best_animal = animal

    if best_animal is None or best_score < similarity_threshold:
        return {
            "model_configured": True,
            "match_found": False,
            "similarity": best_score if best_score >= 0 else 0.0,
            "message": "No confident match found for this cow's voice.",
        }

    return {
        "model_configured": True,
        "match_found": True,
        "similarity": best_score,
        "animal": {
            "id": best_animal.get("id"),
            "animal_name": best_animal.get("animal_name"),
            "breed": best_animal.get("breed"),
            "tag_id": best_animal.get("tag_id"),
            "audio_path": best_animal.get("audio_path"),
        },
        "message": (
            f"Identified cow '{best_animal.get('animal_name')}' by voice "
            f"with similarity score {best_score:.2f}."
        ),
    }


