"""Build the World Sports Calendar.

python3 build.py            -> index.html + sports-diary.ics (the GitHub Pages site)
python3 build.py --artifact -> artifact.html (body-only page for the Claude artifact)

Edit data.json, then run this. Never edit index.html by hand.
"""
import hashlib, json, sys, datetime as dt, calendar, re

HERE = __file__.rsplit('/', 1)[0] if '/' in __file__ else '.'
data = json.load(open(f'{HERE}/data.json'))
tpl = open(f'{HERE}/template.html').read()

# basic validation
for e in data['events']:
    if 'd' in e:
        s = dt.date.fromisoformat(e['d']); en = dt.date.fromisoformat(e.get('e', e['d']))
        assert en >= s, f"end before start: {e['t']}"
    else:
        assert re.fullmatch(r'\d{4}-\d{2}', e['m']), f"bad month: {e['t']}"

page = tpl.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))

if '--artifact' in sys.argv:
    open(f'{HERE}/artifact.html', 'w').write(page)
    sys.exit()

# standalone site: split the template's head material from its body
cut = page.index('<div class="wrap">')
head, body = page[:cut], page[cut:]
reset = ('<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
         'body{margin:0;font:14px/1.45 system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>')
html = ('<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
        + reset + '\n' + head + '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
open(f'{HERE}/index.html', 'w').write(html)

# subscribable calendar feed (all-day events)
PL = {'tv': 'BBC TV', 'ip': 'iPlayer', 'rb': 'Red Button', 'r': '5 Live', 'on': 'Online'}
def esc(s): return s.replace('\\', '\\\\').replace(';', r'\;').replace(',', r'\,').replace('\n', r'\n')
def fold(line):
    out, b = [], line.encode()
    while len(b) > 74:
        cut = 74
        while (b[cut] & 0xC0) == 0x80: cut -= 1
        out.append(b[:cut].decode()); b = b' ' + b[cut:]
    out.append(b.decode()); return '\r\n'.join(out)
stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Sports Planning Diary//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
     'X-WR-CALNAME:World Sports Calendar', 'X-WR-TIMEZONE:Europe/London', 'REFRESH-INTERVAL;VALUE=DURATION:P1D',
     'X-PUBLISHED-TTL:P1D']
for i, e in enumerate(data['events']):
    if 'd' not in e: continue
    s = dt.date.fromisoformat(e['d']); en = dt.date.fromisoformat(e.get('e', e['d'])) + dt.timedelta(days=1)
    live = any(p in e.get('bbc', []) for p in ('tv', 'ip', 'rb'))
    desc = [e['s'], 'BBC: ' + ', '.join(PL[p] for p in e.get('bbc', []))]
    if e.get('time'): desc.append('Time: ' + e['time'] + ' UK')
    if e.get('other'): desc.append('Also: ' + e['other'])
    if e.get('st') == 'p': desc.append('Provisional')
    if e.get('st') == 'r': desc.append('Rights TBC')
    if e.get('note'): desc.append(e['note'])
    desc.append('From World Sports Calendar')
    uid = e['d'].replace('-', '') + '-' + hashlib.sha1(e['t'].encode()).hexdigest()[:12]
    L += ['BEGIN:VEVENT', f'UID:{uid}@world-sports-calendar', f'DTSTAMP:{stamp}',
          f"DTSTART;VALUE=DATE:{s:%Y%m%d}", f"DTEND;VALUE=DATE:{en:%Y%m%d}",
          fold('SUMMARY:' + esc(('★ ' if e.get('k') else '') + ('[BBC] ' if live else '') + (e['time'] + ' ' if e.get('time') else '') + e['t'])),
          fold('DESCRIPTION:' + esc('\n'.join(desc))), 'CATEGORIES:World Sports Calendar', 'TRANSP:TRANSPARENT',
          'X-MICROSOFT-CDO-BUSYSTATUS:FREE', 'X-MICROSOFT-CDO-ALLDAYEVENT:TRUE']
    if e.get('loc'): L.append(fold('LOCATION:' + esc(e['loc'])))
    L.append('END:VEVENT')
L.append('END:VCALENDAR')
_uids = [l for l in L if l.startswith('UID:')]
if len(_uids) != len(set(_uids)):
    import collections
    raise SystemExit('Duplicate events in data.json: ' + ', '.join(u for u, n in collections.Counter(_uids).items() if n > 1))
L = [fold(l) if '\r\n' not in l and len(l.encode()) > 75 else l for l in L]
open(f'{HERE}/sports-diary.ics', 'w', newline='').write('\r\n'.join(L) + '\r\n')
print('built index.html and sports-diary.ics')
