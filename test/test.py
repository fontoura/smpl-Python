import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

import unittest

from simulation_smpl import Rand, Smpl, RESERVED, QUEUED

class TestRand(unittest.TestCase):
    def test_stream_must_be_between_1_and_15(self):
        rand = Rand()

        log = []

        for s in range(-1, 18):
            ok = True
            try:
                rand.stream(s)
            except:
                ok = False
            
            log.append((s, 'ok' if ok else 'not ok'))
        
        self.assertEqual(log, [
            (-1, 'not ok'),
            (0, 'not ok'),
            (1, 'ok'),
            (2, 'ok'),
            (3, 'ok'),
            (4, 'ok'),
            (5, 'ok'),
            (6, 'ok'),
            (7, 'ok'),
            (8, 'ok'),
            (9, 'ok'),
            (10, 'ok'),
            (11, 'ok'),
            (12, 'ok'),
            (13, 'ok'),
            (14, 'ok'),
            (15, 'ok'),
            (16, 'not ok'),
            (17, 'not ok'),
        ])

    def test_ranf_matches_original_smpl(self):
        # the 'expected'' dictionary below has been generated from the C version of Smpl using the following code:
        # for (int s = 1; s < 16; s ++)
        # {
        #   stream(s);
        #   printf("%d: [", s);
        #   for (int i = 0; i < 16; i ++)
        #   {
        #     if (i) printf(", ");
        #     double x = ranf();
        #     // https://stackoverflow.com/a/4654490
        #     printf("%.17g", x);
        #   }
        #   printf("],s\n");
        # }

        expected = {
            1: [0.56245893402895986, 0.2473047237001694, 0.4504914481190157, 0.40976893592780461, 0.98650650208568313, 0.21478142924161403, 0.83148145430592346, 0.70880325726627269, 0.85634550301324364, 0.59886990326036971, 0.20646462830857423, 0.051008165369381291, 0.29423540842760482, 0.21450970377316431, 0.26459150586025748, 0.98943922802679363],
            2: [0.68740082653680878, 0.14569221396426552, 0.64904022662689398, 0.4190894939804376, 0.63712570097525845, 0.17165685638422096, 0.036785401884753093, 0.25224950966595489, 0.55750917945723677, 0.056779632368284955, 0.29528126412155575, 0.79220635290369712, 0.61217395520898599, 0.80766574047324891, 0.43810085039047547, 0.16099290137306962],
            3: [0.16541815416266553, 0.18291715866056402, 0.28868577035887266, 0.94174267763038755, 0.86918376934279618, 0.37161211545089656, 0.68482471285723023, 0.84894959896463806, 0.29591055180056391, 0.36864437457493376, 0.80600380791101622, 0.50600027546689064, 0.34663022091022616, 0.81412314564075283, 0.96770950633008779, 0.29367374827171894],
            4: [0.37819969017772437, 0.40219315251177318, 0.66031462214210324, 0.90785492807857049, 0.31777702191926344, 0.8784076789295473, 0.39786054815759958, 0.84223323769251024, 0.41402664518314192, 0.54582596033995723, 0.69691591785192397, 0.065831955549479307, 0.43767697847823828, 0.036977672033377977, 0.48373389776279258, 0.11562012839248131],
            5: [0.1622328982426986, 0.64832090892588312, 0.32951689245745769, 0.19041182481163552, 0.25153977806820849, 0.62905021550028817, 0.44697247138074903, 0.26632689276530302, 0.15608694271109713, 0.3532462838633007, 0.010293203875947014, 0.99787755212037099, 0.32801937232298645, 0.021590923433724565, 0.8786501697167064, 0.4734032081532018],
            6: [0.44763623615582243, 0.42222146800456617, 0.27621312730242653, 0.31403081690819667, 0.91594005460483707, 0.20449855606133019, 0.0072319041967448504, 0.54661384107761701, 0.93882747638617081, 0.87339645520522902, 0.17422340910624459, 0.17283700320555143, 0.87151302898895167, 0.51947899044519019, 0.88339287311921688, 0.18401929836867378],
            7: [0.23606776129887841, 0.59086435964512063, 0.65729307969230533, 0.12479097168457016, 0.36186121325979143, 0.80141157829694853, 0.3243971477670714, 0.14286280894962547, 0.095230143090912822, 0.53301501342681967, 0.38333113740192687, 0.64642665422202639, 0.49277808304732656, 0.12124221357866141, 0.71788372408436096, 0.47175132269890818],
            8: [0.16099767160729878, 0.88786684665234006, 0.37809247352892267, 0.60020293599561214, 0.61074581069011036, 0.8048408104635818, 0.95950217538081994, 0.35306247664291485, 0.92104525063961806, 0.0075283171640126755, 0.52842658221187422, 0.26556770374787253, 0.39639712607090549, 0.24649822535857407, 0.8956738201874056, 0.58989668429038944],
            9: [0.69182348792133974, 0.47736210768262455, 0.024944245359914713, 0.23793178620327327, 0.91953092944589376, 0.55633201286814626, 0.27214076846898189, 0.86989589956183455, 0.34038470746101851, 0.845778599264988, 0.00091859698333520009, 0.43885949970647375, 0.91161195598928135, 0.46214512056194212, 0.27304169453777904, 0.011760338680086312],
            10: [0.89005505842583443, 0.15536775260127905, 0.26581810751729024, 0.60493327888490722, 0.11361875529435447, 0.59042033298103791, 0.19453693608403461, 0.58228493692180172, 0.46293536127100693, 0.55461729247670122, 0.4528351479216966, 0.80033152164407584, 0.17188498198632204, 0.87089239655629425, 0.08850969424400329, 0.582431237453786],
            11: [0.14155100105586726, 0.047674871535166516, 0.27156593382395011, 0.20865002003731148, 0.78088695215637349, 0.36700558491302848, 0.26286595884387809, 0.98817052220746771, 0.18196761755335186, 0.32974838059971584, 0.081033031955290422, 0.92216814440565043, 0.88000384381983998, 0.22460386073176944, 0.91708751805738187, 0.48991680398321846],
            12: [0.1671919641775266, 0.99534207996098156, 0.71433878719497745, 0.89199701966293432, 0.79391026622798178, 0.24984519799310914, 0.14824289182733699, 0.51828307353869718, 0.78361742463651651, 0.25805656110346548, 0.15662269486993036, 0.35763281784816359, 0.73476989131955472, 0.27756405959189923, 0.019149807289698676, 0.85081113490945126],
            13: [0.90603418313121975, 0.71651669015888908, 0.49601213607927191, 0.47597152433452122, 0.6534099125207139, 0.86040031526371408, 0.74809940050509738, 0.30662495283031271, 0.44558249106401299, 0.90492770811652334, 0.11999111720658358, 0.69070699746367181, 0.71250698465469375, 0.10489172353083354, 0.91519747572553178, 0.72397533089011445],
            14: [0.62018094749650043, 0.38118512385430575, 0.57837695745416717, 0.78152444525292875, 0.081352059297324392, 0.28406068228737513, 0.20788745590686922, 0.96447161112685931, 0.87436906470696263, 0.52087130558762174, 0.28403347323268524, 0.75058487368072535, 0.079972617826847087, 0.099787886761350822, 0.13501288654269122, 0.16158424277942071],
            15: [0.35931925024771555, 0.078639232120348693, 0.68957431642869882, 0.67553682886015731, 0.74748325192497733, 0.95101576617137273, 0.7219828859158528, 0.36636422822477083, 0.48358409871755542, 0.59794757493313777, 0.7048924316768489, 0.12709981813686555, 0.16664353904675408, 0.77796090659209349, 0.18895778347157813, 0.81346697440429472],
        }
        
        generated = {}
        rand = Rand()
        for s in range(1, 16):
            generated[s] = []
            rand.stream(s)
            for i in range(0, 16):
                x = rand.ranf()
                generated[s].append(x)
        
        self.assertEqual(expected, generated)
    
    def test_uniform_boundaries_must_be_valid(self):
        log = {}
        rand = Rand()
        for a in range(0, 20, 5):
            for b in range(0, 20, 5):
                ok = True
                try:
                    rand.uniform(a, b)
                except:
                    ok = False
                log[(a, b)] = 'ok' if ok else 'not ok'
        
        self.assertEqual(log, {
            (0, 0): "ok",
            (0, 5): "ok",
            (0, 10): "ok",
            (0, 15): "ok",
            (5, 0): "not ok",
            (5, 5): "ok",
            (5, 10): "ok",
            (5, 15): "ok",
            (10, 0): "not ok",
            (10, 5): "not ok",
            (10, 10): "ok",
            (10, 15): "ok",
            (15, 0): "not ok",
            (15, 5): "not ok",
            (15, 10): "not ok",
            (15, 15): "ok",
        })

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
    
    def test_facility_name_is_required(self):
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
