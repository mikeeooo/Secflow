def metrics(truth, predicted):
    tp = sum(y and p for y,p in zip(truth,predicted))
    fp = sum(not y and p for y,p in zip(truth,predicted))
    fn = sum(y and not p for y,p in zip(truth,predicted))
    tn = sum(not y and not p for y,p in zip(truth,predicted))
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,precision=round(precision,3),recall=round(recall,3),f1=round(2*precision*recall/(precision+recall),3) if precision+recall else 0,false_positive_rate=round(fp/(fp+tn),3) if fp+tn else 0,n=len(truth))
