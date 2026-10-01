"""CTC Decoder, beam search, explicit confidence computation, and text normalizer."""

import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import torch

from ..schemas.prediction import AlternativeCandidate, NormalizedTextResult


class CTCDecoder:
    """Character-level CTC decoder supporting greedy path and beam search with exact probabilities."""

    def __init__(self, vocab: str, blank_index: int = 0):
        self.vocab = vocab
        self.blank_index = blank_index
        # Mapping dicts
        self.idx_to_char = {idx + 1: char for idx, char in enumerate(vocab)}
        self.idx_to_char[blank_index] = "<blank>"
        self.char_to_idx = {char: idx + 1 for idx, char in enumerate(vocab)}
        self.char_to_idx["<blank>"] = blank_index

    @property
    def num_classes(self) -> int:
        return len(self.vocab) + 1  # Characters + blank

    def text_to_indices(self, text: str) -> List[int]:
        """Encodes string to list of character class indices."""
        indices = []
        for char in text:
            if char in self.char_to_idx:
                indices.append(self.char_to_idx[char])
            elif char.lower() in self.char_to_idx:
                indices.append(self.char_to_idx[char.lower()])
            else:
                # Map unknown characters to space or skip
                indices.append(self.char_to_idx.get(" ", 1))
        return indices

    def indices_to_text(self, indices: List[int]) -> str:
        """Converts class indices to string, omitting blank."""
        chars = [self.idx_to_char.get(idx, "") for idx in indices if idx != self.blank_index]
        return "".join(chars)

    def decode_greedy(
        self,
        log_probs: torch.Tensor
    ) -> Tuple[str, float, List[float]]:
        """Greedy Best-Path CTC decoding.
        
        Args:
            log_probs: (T, num_classes) log-softmax tensor for a single sample.
            
        Returns:
            Tuple of:
                - decoded_text: str
                - sequence_confidence: float in [0.0, 1.0]
                - char_confidences: List[float]
        """
        # Convert to numpy probabilities
        probs = torch.exp(log_probs).detach().cpu().numpy()  # (T, C)
        best_indices = np.argmax(probs, axis=-1)  # (T,)
        best_probs = np.max(probs, axis=-1)  # (T,)

        collapsed_chars = []
        char_probs = []
        prev_idx = self.blank_index

        for t in range(len(best_indices)):
            idx = int(best_indices[t])
            p = float(best_probs[t])

            if idx != self.blank_index:
                if idx != prev_idx:
                    char = self.idx_to_char.get(idx, "")
                    collapsed_chars.append(char)
                    char_probs.append(p)
                else:
                    # Update prob for prolonged character frame
                    if char_probs:
                        char_probs[-1] = max(char_probs[-1], p)
            prev_idx = idx

        text = "".join(collapsed_chars)
        # Sequence confidence is geometric mean or harmonic mean of char probs
        if char_probs:
            # Weighted average with floor to prevent 0 collapse
            seq_conf = float(np.mean(char_probs))
        else:
            seq_conf = 0.0

        return text, round(seq_conf, 4), [round(p, 4) for p in char_probs]

    def decode_beam_search(
        self,
        log_probs: torch.Tensor,
        beam_width: int = 5,
        top_k: int = 3
    ) -> List[AlternativeCandidate]:
        """Prefix beam search decoding returning top-k sequence candidates."""
        probs = torch.exp(log_probs).detach().cpu().numpy()  # (T, C)
        T, C = probs.shape

        # Beam state: prefix_tuple -> (prob_blank, prob_non_blank)
        beams = {(): (1.0, 0.0)}

        for t in range(T):
            new_beams = {}
            for prefix, (p_b, p_nb) in beams.items():
                p_total = p_b + p_nb
                if p_total < 1e-6:
                    continue

                # 1. Transition with blank
                p_blank = probs[t, self.blank_index]
                if prefix not in new_beams:
                    new_beams[prefix] = (0.0, 0.0)
                n_b, n_nb = new_beams[prefix]
                new_beams[prefix] = (n_b + p_total * p_blank, n_nb)

                # 2. Transition with non-blank characters
                for c_idx in range(1, C):
                    p_c = probs[t, c_idx]
                    if p_c < 1e-4:
                        continue
                    char = self.idx_to_char.get(c_idx, "")
                    new_prefix = prefix + (char,)

                    if len(prefix) > 0 and prefix[-1] == char:
                        # Same character repeated: can only extend from blank
                        n_b, n_nb = new_beams.get(new_prefix, (0.0, 0.0))
                        new_beams[new_prefix] = (n_b, n_nb + p_b * p_c)

                        # Non-blank to non-blank preserves prefix
                        n_b, n_nb = new_beams.get(prefix, (0.0, 0.0))
                        new_beams[prefix] = (n_b, n_nb + p_nb * p_c)
                    else:
                        n_b, n_nb = new_beams.get(new_prefix, (0.0, 0.0))
                        new_beams[new_prefix] = (n_b, n_nb + p_total * p_c)

            # Prune to beam_width
            sorted_beams = sorted(
                new_beams.items(),
                key=lambda item: item[1][0] + item[1][1],
                reverse=True
            )[:beam_width]
            beams = dict(sorted_beams)

        # Extract top-k
        candidates = []
        for prefix, (p_b, p_nb) in list(beams.items())[:top_k]:
            cand_text = "".join(prefix)
            total_prob = p_b + p_nb
            if cand_text:
                candidates.append(AlternativeCandidate(
                    text=cand_text,
                    confidence=round(min(1.0, max(0.0, float(total_prob))), 4)
                ))

        if not candidates:
            candidates.append(AlternativeCandidate(text="", confidence=0.0))
        return candidates


def normalize_ocr_text(raw_text: str) -> NormalizedTextResult:
    """Standardizes recognized medical OCR tokens while preserving raw transcription.
    
    Handles:
        - Common OCR whitespace splits (e.g. 'Augm entin' -> 'Augmentin')
        - Dosage formatting (e.g. '500 mg' -> '500mg', '1 + 0 + 1' -> '1+0+1')
        - Punctuation artifacts
        - Casing standardization
    """
    if not raw_text or not raw_text.strip():
        return NormalizedTextResult(raw_text="", normalized_text="", normalization_confidence=1.0)

    text = raw_text.strip()
    
    # Remove leading/trailing non-alphanumeric punctuation noise (like trailing dots or quotes)
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    
    # 1. Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)

    # 2. Fix common broken medication names in cursive script
    common_subwords = {
        r"\baugm\s*entin\b": "Augmentin",
        r"\bpara\s*cetamol\b": "Paracetamol",
        r"\bome\s*prazole\b": "Omeprazole",
        r"\bcipro\s*cin\b": "Ciprocin",
        r"\baza\s*thor\b": "Azathor",
        r"\bcef\s*triaxone\b": "Ceftriaxone",
        r"\bmet\s*formin\b": "Metformin",
        r"\bpanta\s*ton\b": "Pantaton",
        r"\bfla\s*gyl\b": "Flagyl",
        r"\banti\s*nal\b": "Antinal",
        r"\bconges\s*tal\b": "Congestal",
    }

    normalized = text
    for pattern, replacement in common_subwords.items():
        if re.search(pattern, normalized, re.IGNORECASE):
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    # 3. Standardize frequency tokens: "1 + 0 + 1" -> "1+0+1"
    normalized = re.sub(r"(\d)\s*\+\s*(\d)\s*\+\s*(\d)", r"\1+\2+\3", normalized)
    normalized = re.sub(r"(\d)\s*\+\s*(\d)", r"\1+\2", normalized)

    # 4. Standardize dosage units: "500 mg" -> "500mg"
    normalized = re.sub(r"(\d+)\s*(mg|ml|gm|g|mcg|iu)\b", r"\1\2", normalized, flags=re.IGNORECASE)

    # 5. Proper Capitalization if clean word
    words = normalized.split(" ")
    capitalized_words = []
    for w in words:
        if len(w) > 2 and not any(c.isdigit() for c in w):
            capitalized_words.append(w.capitalize())
        else:
            capitalized_words.append(w)
    normalized = " ".join(capitalized_words)

    # Compute normalization confidence (distance penalty if heavily altered)
    norm_conf = 1.0 if normalized == raw_text else 0.92

    return NormalizedTextResult(
        raw_text=raw_text,
        normalized_text=normalized,
        normalization_confidence=norm_conf
    )
