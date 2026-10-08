"""Causal feature construction. Labels, balances and scenarios are never read."""
import math
from collections import defaultdict, deque

NAMES = ['log amount','amount / prior mean','prior transfers in 60s','prior transfers in 5m','log prior 5m amount','new beneficiary','new device','failed logins','recent incoming transfers']

def build(rows):
    histories = defaultdict(deque)
    stats = defaultdict(lambda: [0,0.0])
    partners, devices, incoming = defaultdict(set), defaultdict(set), defaultdict(deque)
    result = []
    for r in rows:
        sender, recipient, t, amount, device = r.sender_id, r.recipient_id, r.timestamp, float(r.amount), r.device
        h = histories[sender]
        while h and h[0][0] < t-300: h.popleft()
        inc = incoming[sender]
        while inc and inc[0] < t-300: inc.popleft()
        n,total = stats[sender]
        ratio = amount/(total/n) if n and total else 1
        new_device = device not in devices[sender]
        evidence = {'history_count':n,'amount_ratio':round(ratio,2),'recent_count':len(h),'new_device':new_device,'failed_logins':r.failed_logins,'recent_incoming':len(inc)}
        vector = [math.log1p(amount),math.log1p(ratio),sum(ts >= t-60 for ts,_ in h),len(h),math.log1p(sum(a for _,a in h)),int(recipient not in partners[sender]),int(new_device),r.failed_logins,len(inc)]
        result.append((vector,evidence))
        h.append((t,amount)); stats[sender] = [n+1,total+amount]
        partners[sender].add(recipient); devices[sender].add(device); incoming[recipient].append(t)
    return result

class Scaler:
    def fit(self, points):
        self.mean = [sum(col)/len(col) for col in zip(*points)]
        self.std = [max(1.0,(sum((x-m)**2 for x in col)/len(col))**.5) for m,col in zip(self.mean,zip(*points))]
        return self
    def transform(self,p): return [(x-m)/s for x,m,s in zip(p,self.mean,self.std)]
