from concurrent.futures import ThreadPoolExecutor
from threading import Event,Lock
import hashlib,json
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime,timezone
import uuid
from core.engine import analyze
from core.ingestion import digest

EXECUTOR=ThreadPoolExecutor(max_workers=2,thread_name_prefix='qsentinel')
CACHE=OrderedDict(); LOCK=Lock()

class AnalysisJob:
    def __init__(self,bits,metadata,size,weights,reference=None):
        self.cancel=Event(); self.progress=0.; self.message='Queued'; self.bits=bits
        key=hashlib.sha256(json.dumps([digest(bits),size,weights,digest(reference) if reference is not None else None],sort_keys=True).encode()).hexdigest()
        def run():
            with LOCK: cached=deepcopy(CACHE.get(key))
            if cached:
                cached.update(session_id=str(uuid.uuid4()),timestamp=datetime.now(timezone.utc).isoformat())
                cached['metadata']=dict(metadata,bits=len(bits),sha256=digest(bits)); self.progress=1.; self.message='Loaded computed analysis from cache'
                return cached
            result=analyze(bits,metadata,size,weights,reference,self.update,self.cancel)
            with LOCK:
                CACHE[key]=deepcopy(result)
                while len(CACHE)>4: CACHE.popitem(last=False)
            return result
        self.future=EXECUTOR.submit(run)
    def update(self,value,message): self.progress=value; self.message=message
