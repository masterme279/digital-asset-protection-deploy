from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_pipeline.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModalityMetrics:
	modality: str
	originals: int
	positives: int
	negatives: int
	true_positives: int
	false_positives: int
	true_negatives: int
	false_negatives: int
	precision: float
	recall: float
	accuracy: float


def _safe_ratio(num: float, den: float) -> float:
	if den == 0:
		return 0.0
	return round(num / den, 4)


def _list_files(folder: Path, exts: tuple[str, ...]) -> list[Path]:
	if not folder.exists():
		return []
	files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in exts]
	return sorted(files)


def _build_metrics(
	modality: str,
	originals: int,
	positives: int,
	negatives: int,
	tp: int,
	fp: int,
	tn: int,
	fn: int,
) -> ModalityMetrics:
	precision = _safe_ratio(tp, tp + fp)
	recall = _safe_ratio(tp, tp + fn)
	accuracy = _safe_ratio(tp + tn, tp + tn + fp + fn)
	return ModalityMetrics(
		modality=modality,
		originals=originals,
		positives=positives,
		negatives=negatives,
		true_positives=tp,
		false_positives=fp,
		true_negatives=tn,
		false_negatives=fn,
		precision=precision,
		recall=recall,
		accuracy=accuracy,
	)


def _print_metrics(metrics: ModalityMetrics) -> None:
	print("\n" + "=" * 72)
	print(f"{metrics.modality.upper()} EVALUATION")
	print("=" * 72)
	print(f"originals: {metrics.originals}")
	print(f"positives: {metrics.positives} | negatives: {metrics.negatives}")
	print(f"TP={metrics.true_positives} FP={metrics.false_positives} TN={metrics.true_negatives} FN={metrics.false_negatives}")
	print(f"precision={metrics.precision:.4f} recall={metrics.recall:.4f} accuracy={metrics.accuracy:.4f}")


def _evaluate_image(dataset_root: Path) -> ModalityMetrics:
	from ai_pipeline.image.detector import ImageDetector

	detector = ImageDetector()

	orig_dir = dataset_root / "image" / "original"
	pos_dir = dataset_root / "image" / "positive"
	neg_dir = dataset_root / "image" / "negative"
	exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

	originals = _list_files(orig_dir, exts)
	positives = _list_files(pos_dir, exts)
	negatives = _list_files(neg_dir, exts)

	if not originals:
		logger.warning("No image originals found at %s", orig_dir)

	tp = fp = tn = fn = 0

	for suspect in positives:
		best = None
		for original in originals:
			result = detector.compare(original, suspect)
			if best is None or result["combined_score"] > best["combined_score"]:
				best = result
		if best and best["is_match"]:
			tp += 1
		else:
			fn += 1

	for suspect in negatives:
		best = None
		for original in originals:
			result = detector.compare(original, suspect)
			if best is None or result["combined_score"] > best["combined_score"]:
				best = result
		if best and best["is_match"]:
			fp += 1
		else:
			tn += 1

	return _build_metrics("image", len(originals), len(positives), len(negatives), tp, fp, tn, fn)


def _evaluate_video(dataset_root: Path) -> ModalityMetrics:
	from ai_pipeline.image.processor import ImageProcessor
	from ai_pipeline.video.analyzer import VideoAnalyzer
	from ai_pipeline.video.frame_extractor import FrameExtractor
	from ai_pipeline.video.processor import VideoProcessor

	processor = VideoProcessor(image_processor=ImageProcessor(), frame_extractor=FrameExtractor())
	analyzer = VideoAnalyzer()

	orig_dir = dataset_root / "video" / "original"
	pos_dir = dataset_root / "video" / "positive"
	neg_dir = dataset_root / "video" / "negative"
	exts = (".mp4", ".avi", ".mov", ".mkv", ".flv")

	originals = _list_files(orig_dir, exts)
	positives = _list_files(pos_dir, exts)
	negatives = _list_files(neg_dir, exts)

	if not originals:
		logger.warning("No video originals found at %s", orig_dir)

	original_fps: dict[Path, dict[str, Any]] = {}
	for original in originals:
		original_fps[original] = processor.fingerprint_video(original)

	tp = fp = tn = fn = 0

	for suspect in positives:
		suspect_fp = processor.fingerprint_video(suspect)
		best = None
		for original in originals:
			result = analyzer.compare(original_fps[original], suspect_fp)
			if best is None or result["combined_score"] > best["combined_score"]:
				best = result
		if best and best["is_match"]:
			tp += 1
		else:
			fn += 1

	for suspect in negatives:
		suspect_fp = processor.fingerprint_video(suspect)
		best = None
		for original in originals:
			result = analyzer.compare(original_fps[original], suspect_fp)
			if best is None or result["combined_score"] > best["combined_score"]:
				best = result
		if best and best["is_match"]:
			fp += 1
		else:
			tn += 1

	return _build_metrics("video", len(originals), len(positives), len(negatives), tp, fp, tn, fn)


def _evaluate_audio(dataset_root: Path, audio_device: str) -> ModalityMetrics:
	from ai_pipeline.audio.analyzer import AudioAnalyzer
	from ai_pipeline.audio.processor import AudioProcessor

	processor = AudioProcessor()
	analyzer = AudioAnalyzer(device=audio_device)

	orig_dir = dataset_root / "audio" / "original"
	pos_dir = dataset_root / "audio" / "positive"
	neg_dir = dataset_root / "audio" / "negative"
	exts = (".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".mp4", ".opus", ".webm")

	originals = _list_files(orig_dir, exts)
	positives = _list_files(pos_dir, exts)
	negatives = _list_files(neg_dir, exts)

	if not originals:
		logger.warning("No audio originals found at %s", orig_dir)

	# Cache full chunk-level signatures for each original once.
	original_repr: dict[Path, tuple[list[Any], Any]] = {}
	for original in originals:
		chunks, meta = processor.process_file(original)
		original_repr[original] = (chunks, meta)

	tp = fp = tn = fn = 0

	for suspect in positives:
		suspect_chunks, suspect_meta = processor.process_file(suspect)
		best_score = -1.0
		best_verdict = "NO_MATCH"
		for original in originals:
			original_chunks, original_meta = original_repr[original]
			report = analyzer.detect_piracy(
				original_chunks,
				original_meta,
				suspect_chunks,
				suspect_meta,
			)
			if report.overall_score > best_score:
				best_score = report.overall_score
				best_verdict = report.verdict
		if best_verdict in {"MATCH", "PARTIAL"}:
			tp += 1
		else:
			fn += 1

	for suspect in negatives:
		suspect_chunks, suspect_meta = processor.process_file(suspect)
		best_score = -1.0
		best_verdict = "NO_MATCH"
		for original in originals:
			original_chunks, original_meta = original_repr[original]
			report = analyzer.detect_piracy(
				original_chunks,
				original_meta,
				suspect_chunks,
				suspect_meta,
			)
			if report.overall_score > best_score:
				best_score = report.overall_score
				best_verdict = report.verdict
		if best_verdict in {"MATCH", "PARTIAL"}:
			fp += 1
		else:
			tn += 1

	return _build_metrics("audio", len(originals), len(positives), len(negatives), tp, fp, tn, fn)


def evaluate_dataset(
	dataset_root: Path,
	audio_device: str = "cpu",
	modalities: list[str] | None = None,
) -> dict[str, Any]:
	start = time.time()
	selected = modalities or ["image", "video", "audio"]
	report: dict[str, Any] = {
		"dataset_root": str(dataset_root.resolve()),
		"started_at": start,
		"modalities_selected": selected,
		"modalities": {},
	}

	collected: list[ModalityMetrics] = []

	if "image" in selected:
		image_metrics = _evaluate_image(dataset_root)
		_print_metrics(image_metrics)
		report["modalities"]["image"] = asdict(image_metrics)
		collected.append(image_metrics)

	if "video" in selected:
		video_metrics = _evaluate_video(dataset_root)
		_print_metrics(video_metrics)
		report["modalities"]["video"] = asdict(video_metrics)
		collected.append(video_metrics)

	if "audio" in selected:
		audio_metrics = _evaluate_audio(dataset_root, audio_device=audio_device)
		_print_metrics(audio_metrics)
		report["modalities"]["audio"] = asdict(audio_metrics)
		collected.append(audio_metrics)

	if collected:
		precision = sum(m.precision for m in collected) / len(collected)
		recall = sum(m.recall for m in collected) / len(collected)
		accuracy = sum(m.accuracy for m in collected) / len(collected)
	else:
		precision = recall = accuracy = 0.0

	report["summary"] = {
		"macro_precision": round(precision, 4),
		"macro_recall": round(recall, 4),
		"macro_accuracy": round(accuracy, 4),
		"finished_at": time.time(),
		"elapsed_seconds": round(time.time() - start, 2),
	}
	return report


def quick_check_image(original: Path, candidate: Path) -> dict[str, Any]:
	from ai_pipeline.image.detector import ImageDetector

	detector = ImageDetector()
	return detector.compare(original, candidate)


def quick_check_video(original: Path, candidate: Path) -> dict[str, Any]:
	from ai_pipeline.image.processor import ImageProcessor
	from ai_pipeline.video.analyzer import VideoAnalyzer
	from ai_pipeline.video.frame_extractor import FrameExtractor
	from ai_pipeline.video.processor import VideoProcessor

	processor = VideoProcessor(image_processor=ImageProcessor(), frame_extractor=FrameExtractor())
	analyzer = VideoAnalyzer()
	fp_a = processor.fingerprint_video(original)
	fp_b = processor.fingerprint_video(candidate)
	return analyzer.compare(fp_a, fp_b)


def quick_check_audio(original: Path, candidate: Path, audio_device: str = "cpu") -> dict[str, Any]:
	from ai_pipeline.audio.analyzer import AudioAnalyzer
	from ai_pipeline.audio.processor import AudioProcessor

	processor = AudioProcessor()
	analyzer = AudioAnalyzer(device=audio_device)

	orig_chunks, orig_meta = processor.process_file(original)
	cand_chunks, cand_meta = processor.process_file(candidate)

	report = analyzer.detect_piracy(orig_chunks, orig_meta, cand_chunks, cand_meta)
	return {
		"verdict": report.verdict,
		"overall_score": report.overall_score,
		"matched_chunks": report.matched_chunks,
		"total_chunks": report.total_chunks,
		"match_percentage": round(report.match_percentage, 2),
		"analysis_time_sec": report.analysis_time_sec,
	}


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="Digital Asset Protection real-world runner",
	)
	sub = parser.add_subparsers(dest="command", required=True)

	eval_p = sub.add_parser("evaluate", help="Run full dataset evaluation")
	eval_p.add_argument(
		"--dataset-root",
		type=Path,
		default=Path("data/raw"),
		help="Dataset root containing image/video/audio original|positive|negative folders",
	)
	eval_p.add_argument(
		"--audio-device",
		default="cpu",
		choices=["cpu", "cuda", "auto"],
		help="Audio model device",
	)
	eval_p.add_argument(
		"--output",
		type=Path,
		default=Path("reports/evaluation_report.json"),
		help="Where to write evaluation JSON report",
	)
	eval_p.add_argument(
		"--modalities",
		nargs="+",
		choices=["image", "video", "audio"],
		default=["image", "video", "audio"],
		help="Which modalities to evaluate",
	)

	img_p = sub.add_parser("check-image", help="Quick single image check")
	img_p.add_argument("--original", type=Path, required=True)
	img_p.add_argument("--candidate", type=Path, required=True)

	vid_p = sub.add_parser("check-video", help="Quick single video check")
	vid_p.add_argument("--original", type=Path, required=True)
	vid_p.add_argument("--candidate", type=Path, required=True)

	aud_p = sub.add_parser("check-audio", help="Quick single audio check")
	aud_p.add_argument("--original", type=Path, required=True)
	aud_p.add_argument("--candidate", type=Path, required=True)
	aud_p.add_argument(
		"--audio-device",
		default="cpu",
		choices=["cpu", "cuda", "auto"],
		help="Audio model device",
	)

	return parser


def main() -> None:
	parser = _build_parser()
	args = parser.parse_args()

	if args.command == "evaluate":
		report = evaluate_dataset(
			args.dataset_root,
			audio_device=args.audio_device,
			modalities=args.modalities,
		)
		args.output.parent.mkdir(parents=True, exist_ok=True)
		args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
		print("\n" + "=" * 72)
		print("EVALUATION SUMMARY")
		print("=" * 72)
		print(json.dumps(report["summary"], indent=2))
		print(f"\nReport saved to: {args.output}")
		return

	if args.command == "check-image":
		result = quick_check_image(args.original, args.candidate)
		print(json.dumps(result, indent=2))
		return

	if args.command == "check-video":
		result = quick_check_video(args.original, args.candidate)
		print(json.dumps(result, indent=2))
		return

	if args.command == "check-audio":
		result = quick_check_audio(args.original, args.candidate, audio_device=args.audio_device)
		print(json.dumps(result, indent=2))
		return

	parser.print_help()


if __name__ == "__main__":
	main()
