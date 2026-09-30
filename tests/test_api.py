import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import validate_request


class SubmissionValidation(unittest.TestCase):
    def test_valid_request(self):
        request = validate_request({'prompt':'  An object jumps.  ', 'rig':'mixamo'}, {'mixamo'})
        self.assertEqual(request['prompt'], 'An object jumps.')
        self.assertEqual(request['seed'], 42)

    def test_untrusted_input_cannot_select_host_paths(self):
        for rig in ['../../secret', {}, [], None]:
            with self.subTest(rig=rig), self.assertRaises(ValueError):
                validate_request({'prompt':'An object jumps.', 'rig':rig}, {'mixamo'})

    def test_seed_and_guidance_are_bounded_finite_numbers(self):
        for field, value in [('seed',True),('seed',-1),('seed',3.5),('seed',2**32),
                             ('guidance',float('nan')),('guidance',float('inf')),('guidance',True)]:
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                validate_request({'prompt':'An object jumps.', 'rig':'mixamo',field:value}, {'mixamo'})

    def test_prompt_and_quality_are_bounded(self):
        for patch in [{'prompt':'  '},{'prompt':'a'*401},{'prompt':123},{'quality':'shell command'}]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_request({'prompt':'An object jumps.', 'rig':'mixamo',**patch}, {'mixamo'})


if __name__ == '__main__':
    unittest.main()
