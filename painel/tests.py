# ==============================================================================
#                                  IMPORTS
# ==============================================================================
from django.test import TestCase


# ==============================================================================
#                                 TEST SUITE
# ==============================================================================

class AppSanityTest(TestCase):
    """
    Testes de infraestrutura básica para assegurar que a suíte de testes do 
    Django e o carregamento da aplicação estão operacionais.
    """
    
    def test_framework_loaded(self) -> None:
        """Verifica a asserção base do framework de testes."""
        self.assertTrue(True)