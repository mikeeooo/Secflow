"""Build features from earlier requests. Never read labels, balances or scenarios."""
import math
from collections import defaultdict, deque

from .algorithms import validate, validate_point

NAMES = ['log amount', 'amount / prior mean', 'prior transfers in 60s', 'prior transfers in 5m',
         'log prior 5m amount', 'new beneficiary', 'new device', 'failed logins', 'recent incoming transfers']


def build(rows):
    histories = defaultdict(deque)
    stats = defaultdict(lambda: [0, 0.0])
    partners, devices, incoming = defaultdict(set), defaultdict(set), defaultdict(deque)
    result = []
    previous_time = -1
    for row in rows:
        sender, recipient, timestamp = row.sender_id, row.recipient_id, row.timestamp
        amount, device = float(row.amount), row.device
        if timestamp < previous_time:
            raise ValueError('Feature rows must be in chronological order.')
        previous_time = timestamp
        recent = histories[sender]
        while recent and recent[0][0] < timestamp - 300:
            recent.popleft()
        received = incoming[sender]
        while received and received[0] < timestamp - 300:
            received.popleft()
        count, total = stats[sender]
        ratio = amount / (total / count) if count and total else 1
        new_device = device not in devices[sender]
        evidence = {
            'history_count': count, 'amount_ratio': round(ratio, 2), 'recent_count': len(recent),
            'new_device': new_device, 'failed_logins': row.failed_logins, 'recent_incoming': len(received),
        }
        vector = [
            math.log1p(amount), math.log1p(ratio), sum(t >= timestamp - 60 for t, _ in recent),
            len(recent), math.log1p(sum(value for _, value in recent)),
            int(recipient not in partners[sender]), int(new_device), row.failed_logins, len(received),
        ]
        result.append((vector, evidence))
        # Update history only after extracting this request's features.
        recent.append((timestamp, amount))
        stats[sender] = [count + 1, total + amount]
        partners[sender].add(recipient)
        devices[sender].add(device)
        incoming[recipient].append(timestamp)
    return result


class Scaler:
    """Reference-only centering; standard deviations have a floor of one."""
    def fit(self, points):
        validate(points)
        self.mean = [sum(column) / len(column) for column in zip(*points)]
        self.std = [max(1.0, (sum((value - mean) ** 2 for value in column) / len(column)) ** .5)
                    for mean, column in zip(self.mean, zip(*points))]
        return self

    def transform(self, point):
        validate_point(point, len(self.mean))
        return [(value - mean) / std for value, mean, std in zip(point, self.mean, self.std)]
