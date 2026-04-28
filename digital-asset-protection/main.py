import os
import sys
from pathlib import Path

from ai_pipeline.scripts.run_pipeline import main as run_pipeline_main


if __name__ == "__main__":
	project_root = Path(__file__).resolve().parent
	venv_python = project_root / "venv" / "Scripts" / "python.exe"
	current_python = Path(sys.executable).resolve()

	# Code Runner can launch with a global interpreter; force project venv when available.
	if venv_python.exists() and current_python != venv_python.resolve():
		print(f"Switching interpreter to project venv: {venv_python}")
		os.execv(str(venv_python), [str(venv_python), *sys.argv])

	default_mode = False
	if len(sys.argv) == 1:
		default_mode = True
		print("No command provided. Running default evaluation for image + video + audio...")
		sys.argv.extend([
			"evaluate",
			"--dataset-root",
			"data/raw",
			"--audio-device",
			"cpu",
			"--output",
			"reports/evaluation_report.json",
			"--modalities",
			"image",
			"video",
			"audio",
		])

	try:
		run_pipeline_main()
		if default_mode:
			print("\nDefault evaluation finished.")
			print("For watermark verification run:")
			print("  python -m pytest ai_pipeline/tests/test_watermark.py -v")
	except ModuleNotFoundError as exc:
		if default_mode:
			print(f"\nDependency missing: {exc}")
			print("Install required packages in your active venv, then run again:")
			print("  pip install -r requirements.txt")
			print("  pip install open-clip-torch")
			print("\nOr run help mode:")
			print("  python main.py --help")
			sys.exit(0)
		raise
