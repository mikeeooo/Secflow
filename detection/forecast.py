"""A small transparent alert-volume estimate, separate from fraud detection."""

def estimate(rows, now, hours=6):
    """Weighted mean of the last six hourly alert counts. Uses no fraud labels."""
    buckets = [{'hour': index, 'alerts': 0, 'transfers': 0} for index in range(hours)]
    start = now - hours * 3600
    for timestamp, risk in rows:
        if timestamp < start or timestamp > now:
            continue
        index = min(hours - 1, (timestamp - start) // 3600)
        buckets[index]['transfers'] += 1
        if risk is not None and risk >= 45:
            buckets[index]['alerts'] += 1
    weights = list(range(1, hours + 1))
    expected = sum(bucket['alerts'] * weight for bucket, weight in zip(buckets, weights)) / sum(weights)
    peak = max([bucket['alerts'] for bucket in buckets] + [expected, 1])
    for bucket in buckets:
        bucket['height'] = round(bucket['alerts'] / peak * 100)
        bucket['label'] = hours - bucket['hour']
    return {'expected': round(expected, 1), 'buckets': buckets,
            'forecast_height': round(expected / peak * 100),
            'observed_transfers': sum(bucket['transfers'] for bucket in buckets),
            'observed_alerts': sum(bucket['alerts'] for bucket in buckets), 'hours': hours}
