import numpy as np
from scipy.stats import theilslopes, spearmanr

def forecast(values, threshold=40):
    if len(values)<20: return dict(available=False,reason='At least 20 comparable monitoring windows required.')
    y=np.asarray(values[-20:]); x=np.arange(len(y))
    if np.ptp(y)<1e-8: return dict(available=False,reason='No measurable trend.')
    slope,intercept,low,high=theilslopes(y,x,alpha=.95); rho,p=spearmanr(x,y)
    if high>=0 or rho>-.6 or y[-1]<=threshold:
        return dict(available=False,reason='No consistent worsening trend above the threshold.')
    crossing=(threshold-y[-1])/slope
    return dict(available=True,slope=float(slope),slope_interval=[float(low),float(high)],windows_to_threshold=float(crossing),threshold=threshold,current=float(y[-1]),reason='Conditional linear projection if the last 20-window trend persists; not a guaranteed prediction. Slope interval assumes the trend model and is not a calibrated forecast interval.')
