"""
Train cow face embedding model for identification.
Expects: data/cow_faces/train/cow_1/, cow_2/, ... (one folder per cow with face images).
If missing, uses synthetic data. Output: 1D embedding per image.
Saves: models/cow_face_model.pt — input (1, 3, 224, 224), output (1, embed_dim).
"""
import os
import sys
import argparse

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from torchvision import transforms as T
    from torchvision import models
    from torchvision.datasets import ImageFolder
    HAS_TORCHVISION = True
except ImportError:
    HAS_TORCHVISION = False

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cow_faces")
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
IMG_SIZE = 224
EMBED_DIM = 128
BATCH_SIZE = 16
EPOCHS = 6
LR = 1e-3


def get_transform():
    return T.Compose([
        T.Resize((IMG_SIZE, IMG_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def build_synthetic_dataset(num_samples=160, num_classes=5):
    images = torch.rand(num_samples, 3, IMG_SIZE, IMG_SIZE)
    images = (images - 0.45) / 0.25
    labels = torch.randint(0, num_classes, (num_samples,)).long()
    return TensorDataset(images, labels), num_classes


def get_real_dataset(train_root):
    train_path = os.path.join(train_root, "train")
    if not os.path.isdir(train_path):
        return None, 0
    subdirs = [d for d in os.listdir(train_path) if os.path.isdir(os.path.join(train_path, d))]
    if not subdirs:
        return None, 0
    ds = ImageFolder(train_path, transform=get_transform())
    return ds, len(ds.classes)


class FaceEmbeddingModel(nn.Module):
    """ResNet backbone -> global pool -> fc -> embed_dim. Output shape (batch, embed_dim)."""

    def __init__(self, embed_dim=EMBED_DIM, num_classes=None):
        super().__init__()
        self.embed_dim = embed_dim
        backbone = models.resnet18(weights=None)
        self.features = nn.Sequential(*list(backbone.children())[:-1])  # remove fc
        self.fc = nn.Linear(512, embed_dim)
        self.classifier = nn.Linear(embed_dim, num_classes) if num_classes else None

    def forward(self, x):
        f = self.features(x)
        f = f.view(f.size(0), -1)
        emb = self.fc(f)
        if self.classifier is not None:
            return emb  # training: we use emb for triplet/ce; inference only needs emb
        return emb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=DATA_DIR)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE)
    parser.add_argument("--embed_dim", type=int, default=EMBED_DIM)
    parser.add_argument("--out", default=os.path.join(MODEL_DIR, "cow_face_model.pt"))
    args = parser.parse_args()

    if not HAS_TORCHVISION:
        print("torchvision required")
        sys.exit(1)

    os.makedirs(MODEL_DIR, exist_ok=True)

    dataset, num_classes = get_real_dataset(args.data_dir)
    if dataset is not None and num_classes > 0:
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
        print(f"Real data: {len(dataset)} samples, {num_classes} classes")
    else:
        dataset, num_classes = build_synthetic_dataset()
        loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
        print("Using synthetic data for face embedding demo.")

    model = FaceEmbeddingModel(embed_dim=args.embed_dim, num_classes=num_classes).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            opt.zero_grad()
            emb = model(images)
            logits = model.classifier(emb) if model.classifier is not None else emb
            if model.classifier is not None:
                loss = criterion(logits, labels)
            else:
                loss = torch.tensor(0.0, device=DEVICE)
            loss.backward()
            opt.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{args.epochs} loss: {total_loss/max(len(loader),1):.4f}")

    # Save inference-only model (embedding only)
    model.classifier = None
    model.eval()
    example = torch.rand(1, 3, IMG_SIZE, IMG_SIZE).to(DEVICE)
    traced = torch.jit.trace(model, example)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    traced.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
