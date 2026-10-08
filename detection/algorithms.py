"""Dependency-free detection algorithms. No sklearn or prebuilt estimators."""
import math
import random
from collections import deque


def validate(points):
    if not points or not points[0] or any(len(p) != len(points[0]) or any(not math.isfinite(v) for v in p) for p in points):
        raise ValueError('Expected a nonempty finite rectangular matrix.')


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def average_path(n):
    if n <= 1: return 0.0
    return 2 * sum(1/i for i in range(1,n)) - 2*(n-1)/n


class IsolationForest:
    def __init__(self, trees=40, sample_size=128, seed=42):
        if trees < 1 or sample_size < 2: raise ValueError('Invalid forest parameters.')
        self.trees, self.sample_size, self.seed = trees, sample_size, seed

    def fit(self, points):
        validate(points)
        self.n = min(len(points), self.sample_size)
        if self.n < 2: raise ValueError('At least two reference points required.')
        rng = random.Random(self.seed)
        limit = math.ceil(math.log2(self.n))
        def build(rows, depth):
            varying = [j for j in range(len(rows[0])) if min(p[j] for p in rows) < max(p[j] for p in rows)]
            if len(rows) <= 1 or depth >= limit or not varying: return len(rows)
            j = rng.choice(varying)
            low, high = min(p[j] for p in rows), max(p[j] for p in rows)
            split = low + (high-low)*rng.random()
            left, right = [p for p in rows if p[j] < split], [p for p in rows if p[j] >= split]
            if not left or not right: return len(rows)
            return j, split, build(left,depth+1), build(right,depth+1)
        self.forest = [build(rng.sample(points,self.n),0) for _ in range(self.trees)]
        return self

    def score(self, point):
        def path(node, depth=0):
            if isinstance(node,int): return depth + average_path(node)
            j, split, left, right = node
            return path(left if point[j] < split else right, depth+1)
        return 2 ** (-(sum(path(t) for t in self.forest)/self.trees)/average_path(self.n))


class DBSCAN:
    def __init__(self, eps=1.2, min_samples=5):
        if eps <= 0 or min_samples < 1: raise ValueError('Invalid DBSCAN parameters.')
        self.eps, self.min_samples = eps, min_samples

    def fit_predict(self, points):
        validate(points)
        labels = [None]*len(points)
        def neighbors(i): return [j for j,p in enumerate(points) if distance(points[i],p) <= self.eps]
        cluster = 0
        for i in range(len(points)):
            if labels[i] is not None: continue
            near = neighbors(i)
            if len(near) < self.min_samples:
                labels[i] = -1
                continue
            labels[i] = cluster
            queue, queued = deque(near), set(near)
            while queue:
                j = queue.popleft()
                if labels[j] == -1: labels[j] = cluster
                if labels[j] is not None: continue
                labels[j] = cluster
                expanded = neighbors(j)
                if len(expanded) >= self.min_samples:
                    for k in expanded:
                        if k not in queued: queue.append(k); queued.add(k)
            cluster += 1
        return labels


class LocalOutlierFactor:
    def __init__(self, k=15):
        if k < 1: raise ValueError('k must be positive.')
        self.k = k

    def fit(self, points):
        validate(points)
        if len(points) < 2: raise ValueError('LOF needs two points.')
        self.points, self.neighbors, self.kdist = points, [], []
        k = min(self.k,len(points)-1)
        for i,p in enumerate(points):
            ds = sorted((distance(p,q),j) for j,q in enumerate(points) if i != j)
            cutoff = ds[k-1][0]
            self.kdist.append(cutoff)
            self.neighbors.append([(d,j) for d,j in ds if d <= cutoff])
        self.lrd = [1/max(1e-12,sum(max(self.kdist[j],d) for d,j in ns)/len(ns)) for ns in self.neighbors]
        self.scores = [sum(self.lrd[j]/self.lrd[i] for _,j in ns)/len(ns) for i,ns in enumerate(self.neighbors)]
        return self

    def score(self, point):
        ds = sorted((distance(point,q),j) for j,q in enumerate(self.points))
        cutoff = ds[min(self.k,len(ds))-1][0]
        ns = [(d,j) for d,j in ds if d <= cutoff]
        lrd = 1/max(1e-12,sum(max(self.kdist[j],d) for d,j in ns)/len(ns))
        return sum(self.lrd[j]/lrd for _,j in ns)/len(ns)
