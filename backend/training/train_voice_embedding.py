"""
Train cow voice embedding model for identification.
Expects: data/cow_voice/train/cow_1/, cow_2/, ... with .wav/.mp3 files.
If missing, uses synthetic mel-spectrograms. Inference uses 64-mel log spectrogram.
Saves: models/cow_voice_model.pt — input (1, 64, time), output (1, embed_dim).
"""
import os
import sys
import argparse

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torchaudio
    HAS_TORCHAUDIO = True
except ImportError:
    HAS_TORCHAUDIO = False

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cow_voice")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
SAMPLE_RATE = 16000
N_MELS = 64
MEL_LEN = 128  # time steps for fixed-length input
EMBED_DIM = 64
BATCH_SIZE = 16
EPOCHS = 6
LR = 1e-3


def build_synthetic_mel_dataset(num_samples=150, num_classes=5):
    """Fake mel spectrograms (1, 64, MEL_LEN) and class labels."""
    class DS(Dataset):
        def __init__(self, n, c):
            self.n = n
            self.c = c
        def __len__(self):
            return self.n
        def __getitem__(self, i):
            x = torch.rand(1, N_MELS, MEL_LEN)
            x = torch.log(x + 1e-6)
            y = i % self.c
            return x, y
    return DS(num_samples, num_classes), num_classes


class VoiceEmbeddingModel(nn.Module):
    """CNN on mel spectrogram (1, 64, T) -> embed_dim. Matches ml_models audio input."""

    def __init__(self, embed_dim=EMBED_DIM, num_classes=None):
        super().__init__()
        self.embed_dim = embed_dim
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Linear(128, embed_dim)
        self.classifier = nn.Linear(embed_dim, num_classes) if num_classes else None

    def forward(self, x):
        # x: (B, 1, 64, T)
        if x.dim() == 3:
            x = x.unsqueeze(1)
        f = self.conv(x)
        f = f.view(f.size(0), -1)
        emb = self.fc(f)
        return emb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=DATA_DIR)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE)
    parser.add_argument("--embed_dim", type=int, default=EMBED_DIM)
    parser.add_argument("--out", default=os.path.join(MODEL_DIR, "cow_voice_model.pt"))
    args = parser.parse_args()

    if not HAS_TORCHAUDIO:
        print("torchaudio required. pip install torchaudio")
        sys.exit(1)

    os.makedirs(MODEL_DIR, exist_ok=True)

    dataset, num_classes = build_synthetic_mel_dataset()
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    print("Using synthetic mel-spectrogram data for voice embedding demo.")

    model = VoiceEmbeddingModel(embed_dim=args.embed_dim, num_classes=num_classes).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for batch_x, labels in loader:
            batch_x, labels = batch_x.to(DEVICE), labels.to(DEVICE)
            opt.zero_grad()
            emb = model(batch_x)
            logits = model.classifier(emb)
            loss = criterion(logits, labels)
            loss.backward()
            opt.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{args.epochs} loss: {total_loss/max(len(loader),1):.4f}")

    model.classifier = None
    model.eval()
    example = torch.rand(1, 1, N_MELS, MEL_LEN).to(DEVICE)
    traced = torch.jit.trace(model, example)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    traced.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
