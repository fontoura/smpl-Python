import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import unittest

from simulation_smpl import Smpl, RESERVED, QUEUED

class TestSmpl(unittest.TestCase):
    def test_model_name(self):
        smpl = Smpl()
        smpl.init("Simulation")
        self.assertEqual(smpl.mname(), "Simulation")
    
    def test_facility_name(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        f1 = smpl.facility("Facility1", 1)
        f2 = smpl.facility("Facility2", 1)
        f3 = smpl.facility("Facility3", 1)
        
        self.assertEqual(smpl.fname(f1), "Facility1")
        self.assertEqual(smpl.fname(f2), "Facility2")
        self.assertEqual(smpl.fname(f3), "Facility3")
    
    def test_facility_name_must_be_provided(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        ex = None
        try:
            f = smpl.facility(None, 1)
        except Exception as e:
            ex = e
        
        self.assertNotEqual(ex, None)
    
    def test_facility_must_have_at_least_one_server(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        ex = None
        try:
            f = smpl.facility("Facility", 0)
        except Exception as e:
            ex = e
        
        self.assertNotEqual(ex, None)
    
    def test_cause_does_not_accept_negative_time(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        ex = None
        try:
            smpl.cause(1, -0.1, "TEST")
        except Exception as e:
            ex = e
        
        self.assertNotEqual(ex, None)
    
    def test_cause_when_scheduled_in_order(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        log = []
        
        smpl.schedule(1, 0.1, 'a')
        smpl.schedule(2, 0.2, 'b')
        smpl.schedule(3, 0.3, 'c')
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            log.append((ev, tkn, smpl.time()))
        
        self.assertEqual(log, [
            (1, 'a', 0.1),
            (2, 'b', 0.2),
            (3, 'c', 0.3)
        ])
    
    def test_cause_when_scheduled_out_of_order(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        log = []
        
        smpl.schedule(3, 0.3, 'c')
        smpl.schedule(2, 0.2, 'b')
        smpl.schedule(1, 0.1, 'a')
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            log.append((ev, tkn, smpl.time()))
        
        self.assertEqual(log, [
            (1, 'a', 0.1),
            (2, 'b', 0.2),
            (3, 'c', 0.3)
        ])
    
    def test_cause_when_scheduled_in_a_chain(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        log = []
        
        string = 'abcdefghij'
        
        smpl.schedule(1, 1, 'a')
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            log.append((ev, tkn, smpl.time()))
            if ev < 10:
                smpl.schedule(ev + 1, 1.0, string[ev])
        
        self.assertEqual(log, [
            (1, 'a', 1.0),
            (2, 'b', 2.0),
            (3, 'c', 3.0),
            (4, 'd', 4.0),
            (5, 'e', 5.0),
            (6, 'f', 6.0),
            (7, 'g', 7.0),
            (8, 'h', 8.0),
            (9, 'i', 9.0),
            (10, 'j', 10.0)
        ])
    
    def test_facility_request_and_release_single_server(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        f = smpl.facility("Facility", 1)
        
        EVENT_REQUEST = 1
        EVENT_RELEASE = 2
        
        TOKEN_1 = 1
        TOKEN_2 = 2
        TOKEN_3 = 3
        
        log = []
        
        smpl.schedule(EVENT_REQUEST, 5.0, TOKEN_1)
        smpl.schedule(EVENT_REQUEST, 6.0, TOKEN_2)
        smpl.schedule(EVENT_REQUEST, 8.0, TOKEN_3)
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            
            if ev == EVENT_REQUEST:
                if smpl.request(f, tkn, 0) == RESERVED:
                    smpl.schedule(EVENT_RELEASE, 5.0, tkn)
                    log.append((EVENT_REQUEST, tkn, smpl.time()))
            elif ev == EVENT_RELEASE:
                smpl.release(f, tkn)
                log.append((EVENT_RELEASE, tkn, smpl.time()))
        
        self.assertEqual(log, [
            (EVENT_REQUEST, TOKEN_1, 5.0),
            (EVENT_RELEASE, TOKEN_1, 10.0),
            (EVENT_REQUEST, TOKEN_2, 10.0),
            (EVENT_RELEASE, TOKEN_2, 15.0),
            (EVENT_REQUEST, TOKEN_3, 15.0),
            (EVENT_RELEASE, TOKEN_3, 20.0)
        ])
    
    def test_facility_request_and_release_multiple_servers(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        f = smpl.facility("Facility", 2)
        
        EVENT_REQUEST = 1
        EVENT_RELEASE = 2
        
        TOKEN_1 = 1
        TOKEN_2 = 2
        TOKEN_3 = 3
        
        log = []
        
        smpl.schedule(EVENT_REQUEST, 5.0, TOKEN_1)
        smpl.schedule(EVENT_REQUEST, 6.0, TOKEN_2)
        smpl.schedule(EVENT_REQUEST, 8.0, TOKEN_3)
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            
            if ev == EVENT_REQUEST:
                if smpl.request(f, tkn, 0) == RESERVED:
                    smpl.schedule(EVENT_RELEASE, 5.0, tkn)
                    log.append((EVENT_REQUEST, tkn, smpl.time()))
            elif ev == EVENT_RELEASE:
                smpl.release(f, tkn)
                log.append((EVENT_RELEASE, tkn, smpl.time()))
        
        self.assertEqual(log, [
            (EVENT_REQUEST, TOKEN_1, 5.0),
            (EVENT_REQUEST, TOKEN_2, 6.0),
            (EVENT_RELEASE, TOKEN_1, 10.0),
            (EVENT_REQUEST, TOKEN_3, 10.0),
            (EVENT_RELEASE, TOKEN_2, 11.0),
            (EVENT_RELEASE, TOKEN_3, 15.0)
        ])
    
    def test_facility_preempt_and_release_single_server(self):
        smpl = Smpl()
        smpl.init("Simulation")
        
        f = smpl.facility("Facility", 1)
        
        EVENT_REQUEST = 1
        EVENT_RELEASE = 2
        
        TOKEN_1 = 1
        TOKEN_2 = 2
        TOKEN_3 = 3
        
        log = []
        
        smpl.schedule(EVENT_REQUEST, 5.0, TOKEN_1)
        smpl.schedule(EVENT_REQUEST, 6.0, TOKEN_2)
        smpl.schedule(EVENT_REQUEST, 8.0, TOKEN_3)
        
        while True:
            try:
                (ev, tkn) = smpl.cause()
            except:
                break
            
            if ev == EVENT_REQUEST:
                if smpl.preempt(f, tkn, tkn) == RESERVED:
                    smpl.schedule(EVENT_RELEASE, 5.0, tkn)
                    log.append((EVENT_REQUEST, tkn, smpl.time()))
            elif ev == EVENT_RELEASE:
                smpl.release(f, tkn)
                log.append((EVENT_RELEASE, tkn, smpl.time()))
        
        self.assertEqual(log, [
            (EVENT_REQUEST, TOKEN_1, 5.0),
            (EVENT_REQUEST, TOKEN_2, 6.0),
            (EVENT_REQUEST, TOKEN_3, 8.0),
            (EVENT_RELEASE, TOKEN_3, 13.0),
            (EVENT_RELEASE, TOKEN_2, 16.0),
            (EVENT_RELEASE, TOKEN_1, 20.0)
        ])
    

if __name__ == '__main__':
    unittest.main()
