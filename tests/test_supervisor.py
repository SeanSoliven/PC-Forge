"""Exercise the real Bash supervisor with harmless Apache process stubs."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--bash',default='bash')
args=parser.parse_args()

class SupervisorChecks(unittest.TestCase):
    def run_fixture(self,fail=False):
        with tempfile.TemporaryDirectory(prefix='pc-forge-supervisor-') as folder:
            work=Path(folder)
            (work/'apache2ctl').write_text('#!/bin/bash\nexit 0\n',newline='\n')
            if fail:
                child='#!/bin/bash\nexit 7\n'
            else:
                child='''#!/bin/bash
trap 'echo child-received-SIGTERM >> "$PC_FORGE_TEST_LOG"; exit 0' TERM
echo ready > "$PC_FORGE_TEST_READY"
while :; do sleep 0.05; done
'''
            (work/'apache2-foreground').write_text(child,newline='\n')
            for name in ['apache2ctl','apache2-foreground']: (work/name).chmod(0o755)
            harness=work/'harness.sh'
            harness.write_text('''#!/bin/bash
set -eu
fixture=$(cd "$2" && pwd)
export PATH="$fixture:$PATH" TRAINING_PREVIEW_ENABLED=0
export PC_FORGE_TEST_READY="$fixture/ready" PC_FORGE_TEST_LOG="$fixture/child.log"
"$BASH" "$1" &
supervisor=$!
trap 'kill -TERM "$supervisor" 2>/dev/null || true' EXIT
if [[ "$3" == stop ]]; then
    for unused in {1..100}; do
        [[ -f "$PC_FORGE_TEST_READY" ]] && break
        sleep 0.02
    done
    [[ -f "$PC_FORGE_TEST_READY" ]]
    kill -TERM "$supervisor"
fi
status=0
wait "$supervisor" || status=$?
echo "supervisor-status=$status"
if [[ -f "$PC_FORGE_TEST_LOG" ]]; then cat "$PC_FORGE_TEST_LOG"; fi
trap - EXIT
''',newline='\n')
            return subprocess.run([args.bash,harness.as_posix(),(ROOT/'docker/supervise-pc-forge').as_posix(),work.as_posix(),'fail' if fail else 'stop'],
                                  capture_output=True,text=True,timeout=5,env=os.environ.copy())

    def test_sigterm_is_forwarded_children_reaped_and_exit_zero(self):
        result=self.run_fixture()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('child-received-SIGTERM',result.stdout)
        self.assertIn('supervisor-status=0',result.stdout)
        self.assertIn('received SIGTERM',result.stderr)
        self.assertIn('reaped child',result.stderr)
        self.assertIn('shutdown complete status=0',result.stderr)

    def test_child_failure_is_preserved(self):
        result=self.run_fixture(fail=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('supervisor-status=7',result.stdout)
        self.assertIn('shutdown complete status=7',result.stderr)

    def test_image_overrides_inherited_apache_stop_signal(self):
        directives=[line.strip() for line in (ROOT/'Dockerfile').read_text().splitlines() if line.strip().upper().startswith('STOPSIGNAL ')]
        self.assertEqual(directives,['STOPSIGNAL SIGTERM'])

unittest.main(argv=['supervisor-checks'])
