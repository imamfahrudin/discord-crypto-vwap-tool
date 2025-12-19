import numpy as np
def rsi(closes,period=14):
    d=np.diff(closes); g=np.maximum(d,0); l=-np.minimum(d,0)
    ag,al=g[-period:].mean(),l[-period:].mean()
    if al==0: return 100
    return round(100-(100/(1+ag/al)),2)
