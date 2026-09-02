import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'backend'))
from hdm.domain.tv_wake import TvWakeEvidence, TvWakeState, assess_tv_wake
class TvWakeTests(unittest.TestCase):
 def test_fail_closed_states_and_verified_postcheck(self):
  self.assertEqual(assess_tv_wake(TvWakeEvidence(False,True,True)),TvWakeState.UNSUPPORTED)
  self.assertEqual(assess_tv_wake(TvWakeEvidence(None,True,True)),TvWakeState.UNAVAILABLE)
  self.assertEqual(assess_tv_wake(TvWakeEvidence(True,True,True)),TvWakeState.ATTEMPT_ELIGIBLE)
  self.assertEqual(assess_tv_wake(TvWakeEvidence(True,True,True,True,False,True)),TvWakeState.ATTEMPTED_UNVERIFIED)
  self.assertEqual(assess_tv_wake(TvWakeEvidence(True,True,True,True,True,True)),TvWakeState.VERIFIED_AWAKE)
if __name__=='__main__': unittest.main()
