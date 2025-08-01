import subprocess
import argparse
import sys
import os

def run_script(script_name):
    print(f"\n🚀 Running {script_name} ...\n")
    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"❌ Error running {script_name}")
        sys.exit(result.returncode)

def main(args):
    base_path = os.path.dirname(os.path.abspath(__file__))

    if args.extract or args.all:
        run_script(os.path.join(base_path, "extract_knowledge.py"))

    if args.embed or args.all:
        run_script(os.path.join(base_path, "generate_embedding_knowledge.py"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Knowledge Extraction and Embedding Scripts")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--extract", action="store_true", help="Run only extract_knowledge.py")
    group.add_argument("--embed", action="store_true", help="Run only generate_embedding_knowledge.py")
    group.add_argument("--all", action="store_true", help="Run both scripts in order")

    args = parser.parse_args()
    main(args)
