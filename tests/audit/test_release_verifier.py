"""Verifier path/metadata negatives; no builds, installation or network."""
import unittest
from scripts.verify_sdk_release import safe_name,metadata

class ReleaseVerifierTests(unittest.TestCase):
 def test_path_traversal_absolute_drive_and_empty_rejected(self):
  for value in ['','.','../outside','pkg/../../outside','/absolute','C:/absolute','C:\\absolute','pkg\x00/file']:
   with self.subTest(value=value),self.assertRaises(ValueError):safe_name(value)
 def test_valid_windows_manifest_path_normalizes(self):
  self.assertEqual(safe_name('arkhe_defense\\policy.py').as_posix(),'arkhe_defense/policy.py')
 def test_metadata_is_dynamic_and_mismatches_rejected(self):
  data=b'Name: example-sdk\nVersion: 12.34.56\n\n'
  self.assertEqual(metadata(data,'example-sdk','12.34.56')['Version'],'12.34.56')
  with self.assertRaises(ValueError):metadata(data,'other-sdk','12.34.56')
  with self.assertRaises(ValueError):metadata(data,'example-sdk','0.1.0')

if __name__=='__main__':unittest.main()
