import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from hdm.domain.thermal_health import *
class T(unittest.TestCase):
 def test_optional_fresh_sustained_only(self):
  self.assertEqual(assess_thermal(ThermalReading('ally',None,False,False)),ThermalState.UNAVAILABLE)
  self.assertEqual(assess_thermal(ThermalReading('g1',90,False,True,3)),ThermalState.UNKNOWN)
  self.assertEqual(assess_thermal(ThermalReading('ally',90,True,True,2)),ThermalState.NORMAL)
  self.assertEqual(assess_thermal(ThermalReading('g1',90,True,True,3)),ThermalState.ATTENTION)
