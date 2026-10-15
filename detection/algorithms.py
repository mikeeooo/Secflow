"""Three algorithms implemented from scratch using only the standard library."""
import math
import random
from collections import deque
from functools import lru_cache


def validate(points):
    if (not points or not points[0]
            or any(len(point) != len(points[0]) or any(not math.isfinite(value) for value in point)
                   for point in points)):
        raise ValueError('Expected a nonempty finite rectangular matrix.')


def validate_point(point, dimensions):
    if len(point) != dimensions or any(not math.isfinite(value) for value in point):
        raise ValueError('Point must match the finite reference dimensions.')


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@lru_cache(maxsize=256)
def average_path(n):
    """Expected remaining path length in a leaf containing n observations."""
    if n <= 1:
        return 0.0
    return 2 * sum(1 / i for i in range(1, n)) - 2 * (n - 1) / n


class IsolationForest:
    """Random partitions: shorter mean paths produce larger anomaly scores."""
    def __init__(self, trees=40, sample_size=128, seed=42):
        if trees < 1 or sample_size < 2:
            raise ValueError('Invalid forest parameters.')
        self.trees, self.sample_size, self.seed = trees, sample_size, seed

    def fit(self, points):
        validate(points)
        self.dimensions = len(points[0])
        self.n = min(len(points), self.sample_size)
        if self.n < 2:
            raise ValueError('At least two reference points required.')
        rng = random.Random(self.seed)
        limit = math.ceil(math.log2(self.n))

        def build(rows, depth):
            varying = [j for j in range(self.dimensions)
                       if min(point[j] for point in rows) < max(point[j] for point in rows)]
            if len(rows) <= 1 or depth >= limit or not varying:
                return len(rows)
            feature = rng.choice(varying)
            low = min(point[feature] for point in rows)
            high = max(point[feature] for point in rows)
            split = low + (high - low) * rng.random()
            left = [point for point in rows if point[feature] < split]
            right = [point for point in rows if point[feature] >= split]
            if not left or not right:
                return len(rows)
            return feature, split, build(left, depth + 1), build(right, depth + 1)

        self.forest = [build(rng.sample(points, self.n), 0) for _ in range(self.trees)]
        return self

    def score(self, point):
        if not hasattr(self, 'forest'):
            raise ValueError('Fit Isolation Forest before scoring.')
        validate_point(point, self.dimensions)

        def path(node, depth=0):
            if isinstance(node, int):
                return depth + average_path(node)
            feature, split, left, right = node
            return path(left if point[feature] < split else right, depth + 1)

        mean_path = sum(path(tree) for tree in self.forest) / self.trees
        return 2 ** (-mean_path / average_path(self.n))


class DBSCAN:
    """Expand density-connected groups; -1 means noise in this batch."""
    def __init__(self, eps=1.2, min_samples=5):
        if not math.isfinite(eps) or eps <= 0 or min_samples < 1:
            raise ValueError('Invalid DBSCAN parameters.')
        self.eps, self.min_samples = eps, min_samples

    def fit_predict(self, points):
        validate(points)
        labels = [None] * len(points)

        def neighbors(index):
            return [j for j, point in enumerate(points) if distance(points[index], point) <= self.eps]

        cluster = 0
        for index in range(len(points)):
            if labels[index] is not None:
                continue
            nearby = neighbors(index)
            if len(nearby) < self.min_samples:
                labels[index] = -1
                continue
            labels[index] = cluster
            queue, queued = deque(nearby), set(nearby)
            while queue:
                other = queue.popleft()
                # A previously isolated point can become a border of this group.
                if labels[other] == -1:
                    labels[other] = cluster
                if labels[other] is not None:
                    continue
                labels[other] = cluster
                expanded = neighbors(other)
                if len(expanded) >= self.min_samples:
                    for neighbor in expanded:
                        if neighbor not in queued:
                            queue.append(neighbor)
                            queued.add(neighbor)
            cluster += 1
        return labels


class LocalOutlierFactor:
    """Compare local reachability densities, retaining all tied neighbors."""
    def __init__(self, k=15):
        if k < 1:
            raise ValueError('k must be positive.')
        self.k = k

    def fit(self, points):
        validate(points)
        if len(points) < 2:
            raise ValueError('LOF needs two points.')
        self.points, self.neighbors, self.kdist = points, [], []
        k = min(self.k, len(points) - 1)
        for index, point in enumerate(points):
            distances = sorted((distance(point, other), j) for j, other in enumerate(points) if index != j)
            cutoff = distances[k - 1][0]
            self.kdist.append(cutoff)
            self.neighbors.append([(d, j) for d, j in distances if d <= cutoff])
        self.lrd = [
            1 / max(1e-12, sum(max(self.kdist[j], d) for d, j in nearby) / len(nearby))
            for nearby in self.neighbors
        ]
        self.scores = [sum(self.lrd[j] / self.lrd[i] for _, j in nearby) / len(nearby)
                       for i, nearby in enumerate(self.neighbors)]
        return self

    def score(self, point):
        if not hasattr(self, 'points'):
            raise ValueError('Fit LOF before scoring.')
        validate_point(point, len(self.points[0]))
        distances = sorted((distance(point, other), j) for j, other in enumerate(self.points))
        cutoff = distances[min(self.k, len(distances)) - 1][0]
        nearby = [(d, j) for d, j in distances if d <= cutoff]
        density = 1 / max(1e-12, sum(max(self.kdist[j], d) for d, j in nearby) / len(nearby))
        return sum(self.lrd[j] / density for _, j in nearby) / len(nearby)
