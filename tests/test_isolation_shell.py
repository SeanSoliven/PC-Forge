"""Local regression checks for restricted-PATH calls and failure diagnostics."""
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

class IsolationShellChecks(unittest.TestCase):
    def failure(self,command,env=None):
        with tempfile.TemporaryDirectory(prefix='pc-forge-shell-check-') as folder:
            script=Path(folder)/'fixture.sh'
            script.write_text('#!/bin/bash\nset -Eeuo pipefail\nsource "$1"\n'+command+'\n',encoding='utf-8',newline='\n')
            environment=dict(os.environ,GITHUB_ACTIONS='true',**(env or {}))
            return subprocess.run([args.bash,script.as_posix(),(ROOT/'tests/shell-diagnostics.sh').as_posix()],
                                  text=True,capture_output=True,env=environment)

    def test_missing_command_preserves_127_and_reports_exact_location(self):
        result=self.failure('pc_forge_deliberately_missing_executable')
        self.assertEqual(result.returncode,127)
        self.assertIn('fixture.sh:4 exit=127 command=pc_forge_deliberately_missing_executable',result.stderr)
        self.assertIn('::error file=',result.stderr)

    def test_assertion_failure_is_not_bypassed_or_secret_expanded(self):
        result=self.failure('test "$PC_FORGE_SYNTHETIC_VALUE" = expected',
                            {'PC_FORGE_SYNTHETIC_VALUE':'synthetic-value-must-not-appear-in-log'})
        self.assertEqual(result.returncode,1)
        self.assertIn('fixture.sh:4 exit=1 command=',result.stderr)
        self.assertIn('PC_FORGE_SYNTHETIC_VALUE',result.stderr)
        self.assertNotIn('synthetic-value-must-not-appear-in-log',result.stderr)

    def test_runuser_is_never_resolved_through_the_restricted_path(self):
        for name in ['tests/container-isolation.sh','docker/supervise-pc-forge']:
            source=(ROOT/name).read_text()
            self.assertNotRegex(source,r'(?<![/\w])runuser\s+-u')
            self.assertIn('/usr/sbin/runuser',source)

    def test_shell_files_have_unix_interpreters_and_no_crlf_or_bom(self):
        for name in ['tests/container-isolation.sh','tests/shell-diagnostics.sh','docker/start-pc-forge','docker/supervise-pc-forge']:
            source=(ROOT/name).read_bytes()
            self.assertTrue(source.startswith(b'#!/bin/'))
            self.assertNotIn(b'\r',source)
            self.assertFalse(source.startswith(b'\xef\xbb\xbf'))

unittest.main(argv=['isolation-shell-checks'])
