import unittest
from sessions import resolve_session

class SessionTests(unittest.TestCase):
    identity={'identifier':'opaque|Windows-session-id','device':'headphones'}
    def row(self,device='headphones',identifier='opaque|Windows-session-id',state=1):
        return {'identifier':identifier,'device_id':device,'state':state}
    def test_exact_selection_wins_over_similar_sessions(self):
        self.assertEqual(resolve_session('chosen',{'chosen':self.row(),'other':self.row()},self.identity),'chosen')
    def test_unique_replacement_on_same_endpoint(self):
        self.assertEqual(resolve_session('expired',{'replacement':self.row()},self.identity),'replacement')
    def test_active_session_does_not_silently_win_over_idle_candidate(self):
        self.assertIsNone(resolve_session('expired',{'call':self.row(),'notification':self.row(state=0)},self.identity))
    def test_other_endpoint_is_not_a_replacement(self):
        self.assertIsNone(resolve_session('expired',{'replacement':self.row(device='speakers')},self.identity))
    def test_different_windows_identity_is_not_a_replacement(self):
        self.assertIsNone(resolve_session('expired',{'replacement':self.row(identifier='other')},self.identity))
    def test_legacy_assignment_is_not_inferred_from_id_text(self):
        self.assertIsNone(resolve_session('headphones|Discord|oldpid',{'headphones|Discord|newpid':self.row()}))

if __name__=='__main__': unittest.main()
