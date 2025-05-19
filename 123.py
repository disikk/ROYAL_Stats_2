"""hero_knockout_parser.py  v1.5
================================================
Скрипт считает количество нокаутов Hero на финальном
столе PKO‑турниров GGPoker и копирует первые 5 файлов с KO
в текущий каталог.

**Главный фикс** v1.5: KO засчитывается только если
Hero ПОКРЫВАЛ стек выбывающего (hero_stack ≥ bust_stack).
Предыдущая версия ошибочно давала лишние KO при делёжке
side‑пота.

Запуск
------
```
python hero_knockout_parser.py INPUT [...] [--hero NAME] [--min_bb 100] [--verbose]
```
* `INPUT` — путь(и) к .txt файлам или папкам (рекурсивно).
* `--hero`   — ник (по умолчанию «Hero»).
* `--min_bb` — фильтр уровня (по умолчанию 100).
* `--verbose`— вывод диагностик.
"""

from __future__ import annotations
import re, sys, shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple

MIN_BB_DEFAULT = 100  # 50/100 уровень → BB=100

# ──────────────────────── REGEXES ───────────────────────────
RE_HAND_START = re.compile(r'^Poker Hand #')
RE_BLINDS     = re.compile(r'(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)')
RE_SEAT       = re.compile(r'^Seat \d+: (.+?) \(.*?([\d,]+) in chips\)')
RE_ACTION     = re.compile(r'^(?P<p>[^:]+): (?P<act>posts|bets|calls|raises|all-in|checks|folds)\b(?:.*?)(?P<amt>[\d,]+)?')
RE_RAISE_TO   = re.compile(r'raises [\d,]+ to ([\d,]+)')
RE_UNCALLED   = re.compile(r'^Uncalled bet \(([\d,]+)\) returned to ([^\n]+)')
RE_COLLECTED  = re.compile(r'^([^:]+) collected ([\d,]+) from pot')

CHIP = lambda s: int(s.replace(',', '')) if s else 0
NAME = lambda s: s.strip()

# ──────────────────────── LOGGER ────────────────────────────
class Logger:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    def log(self, *a):
        if self.verbose:
            print(*a)

log = Logger(False)

# ──────────────────────── DATA CLASSES ─────────────────────
class Pot:
    __slots__ = ('size', 'eligible', 'winners')
    def __init__(self, size: int, eligible: Set[str]):
        self.size = size
        self.eligible = eligible
        self.winners: Set[str] = set()

class Hand:
    __slots__ = ('seats','contrib','collects','pots','bb')
    def __init__(self, seats: Dict[str,int], contrib: Dict[str,int], collects: Dict[str,int], pots: List[Pot], bb: float):
        self.seats      = seats
        self.contrib    = contrib
        self.collects   = collects
        self.pots       = pots
        self.bb         = bb

# ──────────────────────── HELPERS ──────────────────────────

def _extract_blinds(header:str)->Tuple[float,float]:
    m = RE_BLINDS.search(header)
    return (0.0,0.0) if not m else tuple(map(float,m.groups()))

def _add(contrib, committed, pl, amount):
    contrib[pl]  = contrib.get(pl,0)+amount
    committed[pl]= committed.get(pl,0)+amount

# side‑pots

def _build_pots(contrib:Dict[str,int])->List[Pot]:
    pots=[]; levels=sorted({v for v in contrib.values() if v>0}); prev=0
    for lv in levels:
        elig={p for p,a in contrib.items() if a>=lv}
        size=(lv-prev)*len(elig)
        pots.append(Pot(size, elig)); prev=lv
    return pots

def _assign_winners(pots:List[Pot], collects:Dict[str,int]):
    rem=collects.copy()
    for pot in sorted(pots, key=lambda p: len(p.eligible)):
        left=pot.size
        for p in pot.eligible:
            take=min(rem.get(p,0), left)
            if take:
                pot.winners.add(p); rem[p]-=take; left-=take
        if left and pot.eligible:
            pot.winners.add(next(iter(pot.eligible)))

# parse single hand

def _parse_hand(lines:List[str], i:int)->Tuple[int,Hand]:
    header=lines[i]; _,bb=_extract_blinds(header); bb=bb or MIN_BB_DEFAULT
    seats={}; i+=1
    while i<len(lines) and not lines[i].startswith('*** HOLE'):
        if (m:=RE_SEAT.match(lines[i])):
            seats[NAME(m.group(1))]=CHIP(m.group(2))
        i+=1
    contrib, committed, collects = {}, {}, {}
    while i<len(lines) and lines[i].strip():
        ln=lines[i]
        if (m:=RE_UNCALLED.match(ln)):
            amt,pl=m.groups(); _add(contrib,committed,NAME(pl), -CHIP(amt))
        elif (m:=RE_ACTION.match(ln)):
            pl,act,amt_s=m.groups(); pl=NAME(pl); amt=CHIP(amt_s)
            if act in {'posts','bets','calls','all-in'}:
                _add(contrib,committed,pl,amt)
            elif act=='raises' and (tm:=RE_RAISE_TO.search(ln)):
                total=CHIP(tm.group(1)); diff=total-committed.get(pl,0)
                _add(contrib,committed,pl,diff)
        elif (m:=RE_COLLECTED.match(ln)):
            pl,amt=m.groups(); collects[NAME(pl)]=collects.get(NAME(pl),0)+CHIP(amt)
        i+=1
    while i<len(lines) and not lines[i].strip(): i+=1
    pots=_build_pots(contrib); _assign_winners(pots,collects)
    return i, Hand(seats, contrib, collects, pots, bb)

# parse file

def _parse_file(path:Path)->List[Hand]:
    lines=path.read_text(encoding='utf-8',errors='ignore').splitlines(); hands=[]; i=0
    while i<len(lines):
        if RE_HAND_START.match(lines[i]): i,h=_parse_hand(lines,i); hands.append(h)
        else: i+=1
    return list(reversed(hands))

# elimination list

def _eliminated(curr:Hand, nxt:Hand|None):
    return [p for p in curr.seats if p not in (nxt.seats if nxt else curr.collects)]

# KO calc with coverage check

def _ko_in_hand(hand:Hand, eliminated:List[str], hero:str, min_bb:float):
    if hand.bb < min_bb or not eliminated or hero not in hand.seats:
        return 0
    hero_stack = hand.seats[hero]
    seat_pot = {p:pot for pot in sorted(hand.pots, key=lambda p: len(p.eligible)) for p in pot.eligible}
    kos=0
    for bust in eliminated:
        if bust==hero: continue
        pot=seat_pot.get(bust)
        covered = hero_stack >= hand.seats[bust]
        if pot and hero in pot.winners and covered:
            kos+=1
            log.log('KO →', bust, 'via pot', pot.size)
    return kos

# count KO per file

def count_hero_kos(files:List[str], hero:str, min_bb:float)->Tuple[int,Dict[str,int]]:
    total=0; per={}
    for fp in files:
        hands=_parse_file(Path(fp)); k=0
        for idx,h in enumerate(hands):
            k+=_ko_in_hand(h, _eliminated(h, hands[idx+1] if idx+1<len(hands) else None), hero, min_bb)
        per[fp]=k; total+=k
    return total, per

# scan paths

def _collect(paths:List[str])->List[str]:
    res=[]
    for p in paths:
        pth=Path(p)
        if pth.is_dir(): res.extend(str(f) for f in pth.rglob('*.txt'))
        elif pth.is_file(): res.append(str(pth))
    return res

# safe copy

def _copy_first(src:Path, dest_dir:Path)->Path:
    dest=dest_dir/src.name
    if not dest.exists(): shutil.copy2(src,dest); return dest
    i=1; stem,suf=dest.stem,dest.suffix
    while True:
        cand=dest_dir/f"{stem}_{i}{suf}"; i+=1
        if not cand.exists(): shutil.copy2(src,cand); return cand

# ───────────────────────── CLI ──────────────────────────────

def main(argv:List[str]|None=None):
    argv=argv or sys.argv[1:]
    if not argv:
        print('Usage: python hero_knockout_parser.py INPUT [...] [--hero NAME] [--min_bb 100] [--verbose]'); sys.exit(1)
    hero='Hero'; min_bb=MIN_BB_DEFAULT; verbose=False
    if '--hero' in argv:
        i=argv.index('--hero'); hero=argv[i+1]; del argv[i:i+2]
    if '--min_bb' in argv:
        i=argv.index('--min_bb'); min_bb=float(argv[i+1]); del argv[i:i+2]
    if '--verbose' in argv:
        verbose=True; argv.remove('--verbose')
    log.verbose=verbose

    files=_collect(argv)
    if not files:
        print('No .txt files found'); sys.exit(1)

    total, per=count_hero_kos(files, hero, min_bb)
    for fp,k in per.items(): print(f'{fp}: {k} KO(s)')
    print('──────────────'); print('TOTAL:',total,'KO(s)')
    sel=[fp for fp,k in per.items() if k>0][:5]
    if sel:
        print('SELECTED:',*sel)
        cwd=Path.cwd()
        for fp in sel:
            print('Copied →', _copy_first(Path(fp), cwd).name)
    else:
        print(f'No KO found with min_bb ≥ {min_bb}')

if __name__=='__main__':
    main()
