import subprocess
import argparse
import sys
import os

def run_script(script_path, extra_args=None, cwd=None):
    print(f"\n🚀 Running {os.path.basename(script_path)} ...\n")
    cmd = [sys.executable, script_path] + (extra_args or [])
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"❌ Error running {os.path.basename(script_path)}")
        sys.exit(result.returncode)

def main(args):
    base_path = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(base_path, "scripts")
    extract_path = os.path.join(scripts_dir, "extract_knowledge.py")
    embed_path = os.path.join(scripts_dir, "generate_embedding_knowledge.py")

    if args.extract or args.all:
        run_script(extract_path, cwd=base_path)

    if args.embed or args.all:
        embed_args = ["--rebuild"] if args.rebuild else []
        run_script(embed_path, extra_args=embed_args, cwd=base_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Knowledge Extraction and Embedding Scripts")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--extract", action="store_true")
    g.add_argument("--embed", action="store_true")
    g.add_argument("--all", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    main(parser.parse_args())
