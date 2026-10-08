import unittest
from detection.algorithms import IsolationForest, DBSCAN, LocalOutlierFactor
from detection.features import build
from types import SimpleNamespace
class AlgorithmTests(unittest.TestCase):
    def test_dbscan_clusters_border_noise(self):
        self.assertEqual(DBSCAN(.3,2).fit_predict([[0.],[.1],[4.],[4.1],[20.]]),[0,0,1,1,-1])
    def test_lof_duplicate_and_tied_neighbors(self):
        model=LocalOutlierFactor(2).fit([[0.],[0.],[0.],[10.]])
        self.assertEqual(model.scores[:3],[1.,1.,1.])
        self.assertGreater(model.scores[-1],10)
        symmetric=LocalOutlierFactor(1).fit([[-1.],[0.],[1.]])
        self.assertEqual(len(symmetric.neighbors[1]),2)
    def test_forest_reproducible_and_outlier(self):
        points=[[i/100] for i in range(100)]
        a=IsolationForest(80,64,42).fit(points)
        b=IsolationForest(80,64,42).fit(points)
        self.assertEqual(a.score([8]),b.score([8]))
        self.assertGreater(a.score([8]),a.score([.5]))
    def test_validation(self):
        for fn in [lambda:DBSCAN(0),lambda:LocalOutlierFactor(0),lambda:IsolationForest(0),lambda:LocalOutlierFactor().fit([[float('nan')]])]:
            with self.assertRaises(ValueError): fn()
    def test_features_only_past_and_no_labels(self):
        def row(t,a): return SimpleNamespace(sender_id='A',recipient_id='B',timestamp=t,amount=a,device='D',failed_logins=0)
        initial=[row(0,10),row(10,20)]
        self.assertEqual(build(initial),build(initial+[row(20,999999)])[:2])
        self.assertEqual(build(initial)[1][1]['amount_ratio'],2)
        self.assertEqual(build(initial)[0][1]['history_count'],0)
