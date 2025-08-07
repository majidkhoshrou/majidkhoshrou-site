import subprocess
import argparse
import sys
import os


def run_script(script_path, extra_args=None):
    print(f"\n🚀 Running {os.path.basename(script_path)} ...\n")
    command = [sys.executable, script_path]
    if extra_args:
        command += extra_args
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"❌ Error running {os.path.basename(script_path)}")
        sys.exit(result.returncode)


def main(args):
    base_path = os.path.dirname(os.path.abspath(__file__))

    if args.extract or args.all:
        run_script(os.path.join(base_path, "extract_knowledge.py"))

    if args.embed or args.all:
        embed_args = ["--rebuild"] if args.rebuild else []
        run_script(os.path.join(base_path, "generate_embedding_knowledge.py"), extra_args=embed_args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Knowledge Extraction and Embedding Scripts")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--extract", action="store_true", help="Run only extract_knowledge.py")
    group.add_argument("--embed", action="store_true", help="Run only generate_embedding_knowledge.py")
    group.add_argument("--all", action="store_true", help="Run both scripts in order")

    parser.add_argument("--rebuild", action="store_true", help="Force full rebuild of embeddings")

    args = parser.parse_args()
    main(args)
