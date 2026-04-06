import logging,os,shutil,time
from pathlib import Path
from typing import List,Optional
logger=logging.getLogger("FileHistory")
SNAP_DIR=os.environ.get("FILE_SNAP_DIR",os.path.join("recovery","file_snaps"))
MAX_SNAPS=int(os.environ.get("FILE_MAX_SNAPS","10"))
class FileHistory:
    def __init__(self,snap_dir=SNAP_DIR,max_snaps=MAX_SNAPS):
        self.dir=Path(snap_dir);self.dir.mkdir(parents=True,exist_ok=True);self.max_snaps=max_snaps
    def snapshot(self,path):
        src=Path(path)
        if not src.exists():return None
        safe=str(path).replace("/","__").replace(chr(92),"__").replace(":","")
        ts=int(time.time()*1000)
        dst=self.dir/f"{safe}__{ts}.bak"
        try:shutil.copy2(src,dst);self._prune(safe);logger.debug(f"snap {path}");return str(dst)
        except Exception as e:logger.error(f"snapshot failed:{e}");return None
    def undo(self,path):
        src=Path(path)
        safe=str(path).replace("/","__").replace(chr(92),"__").replace(":","")
        snaps=sorted(self.dir.glob(f"{safe}__*.bak"),key=lambda x:x.stat().st_mtime,reverse=True)
        if not snaps:logger.warning(f"no snap for {path}");return False
        try:shutil.copy2(snaps[0],src);snaps[0].unlink();logger.info(f"restored {path}");return True
        except Exception as e:logger.error(f"undo failed:{e}");return False
    def list_snaps(self,path):
        safe=str(path).replace("/","__").replace(chr(92),"__").replace(":","")
        return[str(p) for p in sorted(self.dir.glob(f"{safe}__*.bak"),key=lambda x:x.stat().st_mtime,reverse=True)]
    def _prune(self,safe):
        snaps=sorted(self.dir.glob(f"{safe}__*.bak"),key=lambda x:x.stat().st_mtime)
        while len(snaps)>self.max_snaps:snaps.pop(0).unlink()
