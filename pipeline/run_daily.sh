#!/usr/bin/env bash
# Fabrique l'épisode du jour : joueurs -> photos -> vidéo -> latest.json
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT=$(python3 "$ROOT/pipeline/build_episode.py" "$ROOT")
echo "$OUT"
EP=$(echo "$OUT" | grep '^EPISODE_DIR=' | cut -d= -f2-)
NUM=$(echo "$OUT" | grep '^EPISODE_NUM=' | cut -d= -f2-)
for i in 1 2 3; do
  RAW=$(ls "$EP"/p${i}_raw.* | head -1)
  python3 "$ROOT/pipeline/photo.py" "$RAW" "$EP/p${i}_ht.png"
done
mkdir -p "$ROOT/out"
node "$ROOT/pipeline/render.js" "$EP" "$ROOT/out/la-vignette-$NUM.mp4"
python3 - "$EP" "$NUM" "$ROOT" <<'PY'
import json,sys,os
ep=json.load(open(os.path.join(sys.argv[1],'episode.json')));num=sys.argv[2];root=sys.argv[3]
repo=os.environ.get('GITHUB_REPOSITORY','2n94f9rtkz-droid/la-vignette')
latest={'num':ep['num'],'date':ep['date'],'title':ep['title'],'caption':ep['caption'],'answers':ep['answers'],'players':[{'name':p['name'],'clubs':p['clubs']} for p in ep['players']],
        'video_url':f'https://raw.githubusercontent.com/{repo}/media/la-vignette-{num}.mp4'}
json.dump(latest,open(os.path.join(root,'latest.json'),'w'),ensure_ascii=False,indent=1)
print(json.dumps(latest,ensure_ascii=False,indent=1))
PY
# les photos brutes et traitées ne sont pas versionnées
rm -f "$EP"/*_raw.* "$EP"/*_ht.png "$EP"/events.json "$EP"/audio.wav
