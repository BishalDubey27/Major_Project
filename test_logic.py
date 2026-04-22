import unittest
from unified_app import nlp_preprocess, translate_to_isl_grammar

class TestISLLogic(unittest.TestCase):
    
    def test_contraction_expansion(self):
        self.assertEqual(nlp_preprocess("I'm happy"), "i happy")
        self.assertEqual(nlp_preprocess("what's your name"), "your name what")
    
    def test_article_removal(self):
        self.assertEqual(nlp_preprocess("the cat is on a mat"), "cat mat on")
    
    def test_wh_movement(self):
        self.assertEqual(translate_to_isl_grammar("what is your name"), "your name what")
        self.assertEqual(translate_to_isl_grammar("where are you going"), "you going where")
    
    def test_negation_movement(self):
        self.assertEqual(translate_to_isl_grammar("i do not like apple"), "i apple like not")
    
    def test_sov_reordering(self):
        # "i eat apple" -> "i apple eat"
        self.assertEqual(translate_to_isl_grammar("i eat apple"), "i apple eat")
        # "she drinks water" -> "she water drinks"
        self.assertEqual(translate_to_isl_grammar("she drinks water"), "she water drinks")

if __name__ == '__main__':
    unittest.main()
