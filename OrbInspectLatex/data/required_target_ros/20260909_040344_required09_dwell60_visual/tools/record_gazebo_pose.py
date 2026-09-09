"""Retain named Gazebo scene poses, simulator stamps and wall receipt times."""
import argparse
import json
from pathlib import Path
import subprocess
import time


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    command = ['gz', 'topic', '-e', '-t', '/world/iss_real_visual/dynamic_pose/info',
               '--json-output']
    child = subprocess.Popen(command, stdout=subprocess.PIPE, text=True, bufsize=1)
    try:
        with args.output.open('x') as stream:
            for line in child.stdout:
                receipt = time.time_ns()
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                stream.write(json.dumps({'wall_receipt_ns': receipt, 'message': payload})+'\n')
                stream.flush()
    except KeyboardInterrupt:
        pass
    finally:
        child.terminate()
        child.wait(timeout=10)
