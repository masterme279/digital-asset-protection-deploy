import numpy as np
from typing import Union
from pathlib import Path

from ai_pipeline.utils.helpers import cosine_similarity
from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


class VideoAnalyzer:
    """
    Compares two video fingerprints.

    Two comparison modes:
    1. Summary match  — fast, compares mean-pooled embeddings (good for exact copies)
    2. Temporal match — slower, aligns frame sequences (catches partial clips)
    """

    CLIP_WEIGHT  = 0.4
    DINO_WEIGHT  = 0.6

    THRESHOLD_EXACT      = 0.99
    THRESHOLD_HIGH       = 0.95
    THRESHOLD_MEDIUM     = 0.85
    THRESHOLD_SUSPICIOUS = 0.75

    def compare_summary(self, fp_a: dict, fp_b: dict) -> dict:
        """
        Fast comparison using summary (mean-pooled) embeddings.
        Use this for initial screening against a large database.
        """
        clip_score = cosine_similarity(fp_a["clip_summary"], fp_b["clip_summary"])
        dino_score = cosine_similarity(fp_a["dino_summary"], fp_b["dino_summary"])
        combined   = (self.CLIP_WEIGHT * clip_score) + (self.DINO_WEIGHT * dino_score)

        return self._build_result(clip_score, dino_score, combined, mode="summary")

    def compare_temporal(self, fp_a: dict, fp_b: dict,
                          window: int = 5) -> dict:
        """
        Temporal alignment comparison.
        Slides a window across both frame sequences and finds the
        best-matching segment — catches clips that are subsets of longer videos.

        Example: a 10-second clip stolen from a 90-minute broadcast.
        Summary match would score low, but temporal alignment finds the match.
        """
        seq_a = fp_a["clip_temporal"]   # (Na, 512)
        seq_b = fp_b["clip_temporal"]   # (Nb, 512)

        if len(seq_a) < window or len(seq_b) < window:
            # Not enough frames — fall back to summary
            return self.compare_summary(fp_a, fp_b)

        best_score = 0.0
        best_offset = 0

        # Slide seq_b over seq_a to find best alignment window
        for offset in range(len(seq_a) - window + 1):
            window_a = seq_a[offset: offset + window]
            for j in range(len(seq_b) - window + 1):
                window_b = seq_b[j: j + window]
                # Compare window means
                mean_a = window_a.mean(axis=0)
                mean_b = window_b.mean(axis=0)
                score  = cosine_similarity(
                    mean_a / np.linalg.norm(mean_a),
                    mean_b / np.linalg.norm(mean_b)
                )
                if score > best_score:
                    best_score  = score
                    best_offset = offset

        # Also run dino temporal for the best-found window
        dino_a   = fp_a["dino_temporal"]
        dino_b   = fp_b["dino_temporal"]
        dino_win = min(window, len(dino_a), len(dino_b))
        dino_a_w = dino_a[best_offset: best_offset + dino_win].mean(axis=0)
        dino_b_w = dino_b[:dino_win].mean(axis=0)
        dino_score = cosine_similarity(
            dino_a_w / np.linalg.norm(dino_a_w),
            dino_b_w / np.linalg.norm(dino_b_w)
        )

        combined = (self.CLIP_WEIGHT * best_score) + (self.DINO_WEIGHT * dino_score)
        return self._build_result(
            best_score, dino_score, combined,
            mode="temporal",
            best_offset=best_offset
        )

    def compare(self, fp_a: dict, fp_b: dict) -> dict:
        """
        Full comparison: summary first, temporal if summary is suspicious.
        This is the main entry point.
        """
        summary_result = self.compare_summary(fp_a, fp_b)

        # If clearly matching or clearly not — return summary result
        if summary_result["combined_score"] >= self.THRESHOLD_HIGH:
            return summary_result
        if summary_result["combined_score"] < self.THRESHOLD_SUSPICIOUS:
            return summary_result

        # In the grey zone — run temporal alignment for better accuracy
        logger.info(
            f"Summary score {summary_result['combined_score']:.3f} in grey zone — "
            f"running temporal alignment"
        )
        temporal_result = self.compare_temporal(fp_a, fp_b)

        # Take the higher of the two scores
        if temporal_result["combined_score"] > summary_result["combined_score"]:
            logger.info(
                f"Temporal improved score: "
                f"{summary_result['combined_score']:.3f} → "
                f"{temporal_result['combined_score']:.3f}"
            )
            return temporal_result

        return summary_result

    def _build_result(self, clip_score: float, dino_score: float,
                       combined: float, mode: str, **extra) -> dict:
        confidence = self._confidence_label(combined)
        result = {
            "clip_similarity":  round(clip_score, 4),
            "dino_similarity":  round(dino_score, 4),
            "combined_score":   round(combined, 4),
            "is_match":         combined >= self.THRESHOLD_MEDIUM,
            "confidence":       confidence,
            "alert_level":      self._alert_level(combined),
            "action":           self._recommended_action(combined),
            "comparison_mode":  mode,
            **extra
        }
        logger.info(
            f"[{mode.upper()}] CLIP: {clip_score:.3f} | "
            f"DINOv2: {dino_score:.3f} | Combined: {combined:.3f} | "
            f"{confidence} → {result['action']}"
        )
        return result

    def _confidence_label(self, score: float) -> str:
        if score >= self.THRESHOLD_EXACT:        return "EXACT_MATCH"
        elif score >= self.THRESHOLD_HIGH:       return "HIGH"
        elif score >= self.THRESHOLD_MEDIUM:     return "MEDIUM"
        elif score >= self.THRESHOLD_SUSPICIOUS: return "SUSPICIOUS"
        else:                                    return "NO_MATCH"

    def _alert_level(self, score: float) -> str:
        if score >= self.THRESHOLD_EXACT:        return "CRITICAL"
        elif score >= self.THRESHOLD_HIGH:       return "HIGH"
        elif score >= self.THRESHOLD_MEDIUM:     return "MEDIUM"
        elif score >= self.THRESHOLD_SUSPICIOUS: return "LOW"
        else:                                    return "NONE"

    def _recommended_action(self, score: float) -> str:
        if score >= self.THRESHOLD_EXACT:        return "AUTO_TAKEDOWN"
        elif score >= self.THRESHOLD_HIGH:       return "LEGAL_REVIEW"
        elif score >= self.THRESHOLD_MEDIUM:     return "FLAG_FOR_REVIEW"
        elif score >= self.THRESHOLD_SUSPICIOUS: return "MONITOR"
        else:                                    return "IGNORE"