// node render.js <episodeDir> <out.mp4|preview> [t1 t2 ...]
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path'), fs = require('fs');
const epDir = path.resolve(process.argv[2]), mode = process.argv[3];
const ep = JSON.parse(fs.readFileSync(path.join(epDir, 'episode.json'), 'utf8'));
ep.players.forEach(p => p.img = 'file://' + path.join(epDir, p.img));
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 405, height: 720 }, deviceScaleFactor: 1080 / 405 });
  await pg.goto('file://' + path.join(__dirname, 'video.html'));
  await pg.evaluate(e => { setEp(e); render(0); }, ep);
  await pg.evaluate(() => document.fonts.ready);
  const el = await pg.$('#s');
  if (mode === 'preview') {
    for (const t of process.argv.slice(4).map(Number)) {
      await pg.evaluate(t => render(t), t);
      await pg.waitForTimeout(50);
      await el.screenshot({ path: path.join(epDir, `prev_${t}.png`) });
    }
  } else {
    fs.writeFileSync(path.join(epDir, 'events.json'), JSON.stringify(await pg.evaluate(() => events())));
    execFileSync('python3', [path.join(__dirname, 'audio.py'), path.join(epDir, 'events.json'), path.join(epDir, 'audio.wav')], { stdio: 'inherit' });
    // preload images so frames never miss them
    for (const t of [21, 39, 57 - 18 + 15]) { await pg.evaluate(t => render(t), t); }
    await pg.waitForTimeout(300);
    const fps = 30, dur = 60;
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-i', path.join(epDir, 'audio.wav'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium',
      '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', mode], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = 0; f < fps * dur; f++) {
      await pg.evaluate(t => render(t), f / fps);
      const buf = await el.screenshot({ type: 'jpeg', quality: 90 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
