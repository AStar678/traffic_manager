import numpy as np
import torch

from gesture.training.geometry import GEOMETRY_FEATURE_DIM, extract_geometry_features
from gesture.training.model import prototypical_loss


def test_geometry_feature_contract():
    landmarks = np.zeros((21, 3), dtype=np.float32)
    landmarks[:, 0] = np.linspace(0.1, 0.9, 21)
    landmarks[:, 1] = np.linspace(0.2, 0.8, 21) ** 2
    landmarks[:, 2] = np.linspace(-0.1, 0.1, 21)
    features = extract_geometry_features(landmarks)
    assert features.shape == (GEOMETRY_FEATURE_DIM,)
    assert np.isfinite(features).all()


def test_prototypical_loss_separates_easy_episode():
    embeddings = torch.tensor(
        [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [0.1, 0.9]], dtype=torch.float32
    )
    labels = torch.tensor([0, 0, 1, 1])
    loss, accuracy = prototypical_loss(embeddings, labels, n_support=1, temperature=0.1)
    assert loss.item() < 0.01
    assert accuracy.item() == 1.0
