"""
Train Foot-and-Mouth Disease (FMD) binary classifier.
Expects: data/fmd/train/healthy/ and data/fmd/train/diseased/ with images.
If missing, generates a small synthetic dataset so training runs.
Output: models/fmd_model.pt (TorchScript) — input (1, 3, 224, 224), output (1, 2) logits.
"""
import os
import sys
import argparse

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# Add backend root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from torchvision import transforms as T
    from torchvision import models
    from torchvision.datasets import ImageFolder
    HAS_TORCHVISION = True
except ImportError:
    HAS_TORCHVISION = False

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "fmd")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
IMG_SIZE = 224
BATCH_SIZE = 16
EPOCHS = 8
LR = 1e-3


def get_transform():
    return T.Compose([
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def build_synthetic_dataset(num_samples=200):
    """Generate random images and labels when no real data exists."""
    transform = get_transform()
    # Random RGB images (simulate healthy=0, diseased=1)
    images = torch.rand(num_samples, 3, IMG_SIZE, IMG_SIZE)
    images = (images - 0.45) / 0.25  # rough normalize
    labels = torch.randint(0, 2, (num_samples,)).long()
    return TensorDataset(images, labels)


def get_real_dataset(train_path):
    train_path = os.path.join(train_path, "train")
    if not os.path.isdir(train_path):
        return None
    healthy = os.path.join(train_path, "healthy")
    diseased = os.path.join(train_path, "diseased")
    if not os.path.isdir(healthy) or not os.path.isdir(diseased):
        return None
    return ImageFolder(train_path, transform=get_transform())


class FMDClassifier(nn.Module):
    """Binary classifier: 3x224x224 -> 2 logits. Matches inference in ml_models.py."""

    def __init__(self, num_classes=2):
        super().__init__()
        self.backbone = models.resnet18(weights=None)
        self.backbone.fc = nn.Linear(self.backbone.fc.in_features, num_classes)

    def forward(self, x):
        return self.backbone(x)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=DATA_DIR, help="Root containing train/healthy and train/diseased")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--out", default=os.path.join(MODEL_DIR, "fmd_model.pt"))
    args = parser.parse_args()

    if not HAS_TORCHVISION:
        print("torchvision required. pip install torchvision")
        sys.exit(1)

    os.makedirs(MODEL_DIR, exist_ok=True)

    dataset = get_real_dataset(args.data_dir)
    if dataset is not None:
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
        num_classes = len(dataset.classes)
        print(f"Using real data: {len(dataset)} samples, classes: {dataset.classes}")
    else:
        dataset = build_synthetic_dataset()
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
        num_classes = 2
        print("No FMD folder found; using synthetic data for demo training.")

    model = FMDClassifier(num_classes=num_classes).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for batch_idx, (images, labels) in enumerate(loader):
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            opt.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            opt.step()
            total_loss += loss.item()
        avg = total_loss / max(len(loader), 1)
        print(f"Epoch {epoch+1}/{args.epochs} loss: {avg:.4f}")

    model.eval()
    example = torch.rand(1, 3, IMG_SIZE, IMG_SIZE).to(DEVICE)
    traced = torch.jit.trace(model, example)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    traced.save(args.out)
    print(f"Saved TorchScript model to {args.out}")


if __name__ == "__main__":
    main()
