"""PyTorch Dataset for Handwritten Text Recognition (RxHandBD & Clinical Words)."""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
import cv2
import torch
from torch.utils.data import Dataset

from ..config import PrescriptionConfig, default_config
from ..preprocessing.image_preprocessor import PrescriptionImagePreprocessor
from .decoder import CTCDecoder


class PrescriptionHandwritingDataset(Dataset):
    """Dataset for training CRNN + CTC on cropped handwritten medical word tokens."""

    def __init__(
        self,
        metadata_csv: Optional[Path] = None,
        images_dir: Optional[Path] = None,
        split: str = "train",
        config: Optional[PrescriptionConfig] = None
    ):
        self.config = config or default_config
        self.split = split
        self.preprocessor = PrescriptionImagePreprocessor(self.config)
        self.decoder = CTCDecoder(vocab=self.config.recognition_vocab, blank_index=self.config.blank_index)

        self.metadata_csv = metadata_csv or (self.config.data_dir / "metadata" / "rxhandbd_metadata.csv")
        self.images_dir = images_dir or (self.config.data_dir / "raw" / "rxhandbd")

        self.samples = self._load_samples()

    def _load_samples(self) -> List[Dict[str, Any]]:
        """Loads and filters metadata partition."""
        if not self.metadata_csv.exists():
            return []

        df = pd.read_csv(self.metadata_csv)

        if "split" in df.columns:
            if self.split in ("train", "val", "validation", "test"):
                target_split = "val" if self.split == "validation" else self.split
                df_split = df[df["split"] == target_split]
                if not df_split.empty:
                    df = df_split

        samples = df.to_dict(orient="records")
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, int, str]:
        sample = self.samples[idx]
        file_name = sample.get("filename", "")
        img_path = self.images_dir / file_name

        if not img_path.exists():
            # Create synthetic blank word canvas if missing
            bgr = np.full((48, 140, 3), 255, dtype=np.uint8)
        else:
            bgr = cv2.imread(str(img_path))

        # Preprocess for handwriting
        prep = self.preprocessor.preprocess_for_handwriting(bgr)
        tensor_chw = prep["tensor"]  # (1, 64, 256)

        label_text = str(sample.get("transcription", sample.get("label", ""))).strip()
        label_indices = self.decoder.text_to_indices(label_text)

        # Truncate or ensure minimum length
        if len(label_indices) == 0:
            label_indices = [self.decoder.char_to_idx.get(" ", 1)]

        target_tensor = torch.tensor(label_indices, dtype=torch.long)
        target_len = len(label_indices)
        image_tensor = torch.from_numpy(tensor_chw).float()

        return image_tensor, target_tensor, target_len, label_text


def handwriting_collate_fn(batch):
    """Collate function for variable-length target sequences in CTCLoss."""
    images = [item[0] for item in batch]
    targets = [item[1] for item in batch]
    target_lengths = [item[2] for item in batch]
    texts = [item[3] for item in batch]

    images_batch = torch.stack(images, dim=0)  # (B, 1, 64, 256)
    targets_concat = torch.cat(targets, dim=0)  # Concatenated 1D tensor for CTCLoss
    target_lengths_tensor = torch.tensor(target_lengths, dtype=torch.long)

    # In CRNN with our pooling architecture, W=256 reduces to T=66 time steps
    input_lengths_tensor = torch.full(
        size=(len(batch),),
        fill_value=66,
        dtype=torch.long
    )

    return images_batch, targets_concat, input_lengths_tensor, target_lengths_tensor, texts
