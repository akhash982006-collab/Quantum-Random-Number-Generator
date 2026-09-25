"""NIST SP 800-22 rev1a, sections 2.1-2.4, 2.6, 2.13.
Results are screening evidence, never certification. Six families / seven rows.
"""
import math
import numpy as np
from scipy.special import erfc, gammaincc, ndtr

ALPHA = .01

def result(name, statistic=None, p=None, reason='', **parameters):
    p = None if p is None else float(np.clip(p, 0, 1))
    return dict(name=name, family='Cumulative Sums' if name.startswith('Cumulative') else name,
                statistic=None if statistic is None else float(statistic), p_value=p,
                threshold=ALPHA, status='NOT APPLICABLE' if p is None else ('PASS' if p >= ALPHA else 'FAIL'),
                interpretation=reason or ('No rejection at alpha=0.01; not proof of randomness.' if p >= ALPHA else 'Evidence inconsistent with this test null hypothesis.'), parameters=parameters)

def frequency(b, enforce=True):
    n=len(b)
    if n < (100 if enforce else 1): return result('Frequency', reason='Requires at least 100 bits.')
    s=abs(2*int(np.sum(b))-n)/math.sqrt(n)
    return result('Frequency', s, erfc(s/math.sqrt(2)))

def block_frequency(b, m=None, enforce=True):
    n=len(b); m=m or max(20, n//99+1); count=n//m
    if count < 1 or (enforce and (n < 100 or m < 20 or m <= .01*n or count >= 100)):
        return result('Block Frequency', reason='Requires n>=100, M>=20, M>0.01n, and fewer than 100 blocks.')
    stat=4*m*np.sum((b[:count*m].reshape(count,m).mean(axis=1)-.5)**2)
    return result('Block Frequency', stat, gammaincc(count/2,stat/2), block_size=m, blocks=count, discarded=n-count*m)

def runs(b, enforce=True):
    n=len(b)
    if n < (100 if enforce else 2): return result('Runs', reason='Requires at least 100 bits.')
    pi=float(np.mean(b)); v=1+int(np.count_nonzero(np.diff(b.astype(np.int8))))
    if abs(pi-.5)>=2/math.sqrt(n):
        return result('Runs', v, reason='Frequency prerequisite fails: |pi-0.5| >= 2/sqrt(n).', pi=pi)
    p=erfc(abs(v-2*n*pi*(1-pi))/(2*math.sqrt(2*n)*pi*(1-pi)))
    return result('Runs',v,p,pi=pi)

def longest_run(b):
    n=len(b)
    if n<128: return result('Longest Run', reason='Requires at least 128 bits.')
    if n<6272: m=8; cuts=[1,2,3]; probs=[.2148,.3672,.2305,.1875]
    elif n<750000: m=128; cuts=[4,5,6,7,8]; probs=[.1174,.2430,.2493,.1752,.1027,.1124]
    else: m=10000; cuts=[10,11,12,13,14,15]; probs=[.0882,.2092,.2483,.1933,.1208,.0675,.0727]
    count=n//m; matrix=b[:count*m].reshape(count,m)
    # Vectorize across blocks; bounded M keeps the scan memory-efficient.
    current=np.zeros(count,dtype=int); longest=current.copy()
    for col in matrix.T:
        current=(current+1)*col; longest=np.maximum(longest,current)
    bins=np.bincount(np.searchsorted(cuts,longest,side='left'),minlength=len(probs))
    expected=count*np.array(probs); stat=np.sum((bins-expected)**2/expected)
    return result('Longest Run',stat,gammaincc((len(probs)-1)/2,stat/2),block_size=m,blocks=count,discarded=n-count*m)

def dft(b, enforce=True):
    n=len(b)
    if n<(1000 if enforce else 2): return result('DFT',reason='Requires at least 1,000 bits.')
    magnitudes=np.abs(np.fft.rfft(b.astype(float)*2-1))[:n//2]
    observed=int(np.sum(magnitudes<math.sqrt(math.log(20)*n)))
    stat=(observed-.95*n/2)/math.sqrt(n*.95*.05/4)
    return result('DFT',stat,erfc(abs(stat)/math.sqrt(2)),peaks_below_threshold=observed)

def cumulative_sums(b, reverse=False, enforce=True):
    name='Cumulative Sums '+('Backward' if reverse else 'Forward'); n=len(b)
    if n<(100 if enforce else 1): return result(name,reason='Requires at least 100 bits.')
    x=b[::-1] if reverse else b; z=int(np.max(np.abs(np.cumsum(x.astype(np.int64)*2-1))))
    root=math.sqrt(n)
    # NIST reference-code integer loop bounds truncate toward zero.
    k=np.arange(int((-n/z+1)/4),int((n/z-1)/4)+1)
    a=np.sum(ndtr((4*k+1)*z/root)-ndtr((4*k-1)*z/root))
    k=np.arange(int((-n/z-3)/4),int((n/z-1)/4)+1)
    c=np.sum(ndtr((4*k+3)*z/root)-ndtr((4*k+1)*z/root))
    return result(name,z,1-a+c)

def suite(bits):
    return [frequency(bits),block_frequency(bits),runs(bits),longest_run(bits),dft(bits),cumulative_sums(bits),cumulative_sums(bits,True)]

def summary(results):
    families={r['family'] for r in results if r['p_value'] is not None}
    failed={r['family'] for r in results if r['status']=='FAIL'}
    return dict(nist_pass_rate=None if not families else 1-len(failed)/len(families), nist_failures=len(failed), nist_applicable=len(families))
