"""Render the whole film: parallel frame rendering -> H.264 segments -> concat + audio mux."""
import os
import sys
import subprocess
import multiprocessing as mp
import cairo
import importlib
from engine import W, H, FPS

EP = int(sys.argv[2]) if len(sys.argv) > 2 else 1
SCENES = 'scenes' if EP == 1 else f'scenes{EP}'
TLM = importlib.import_module('timeline' if EP == 1 else f'timeline{EP}')
TOTAL, ROOT = TLM.TOTAL, TLM.ROOT
BUILD = {1: os.path.join(ROOT, 'build'), 3: os.path.join(ROOT, 'build', 'train')}.get(EP, os.path.join(ROOT, 'build', f'ep{EP}'))
FINAL = os.path.join(ROOT, 'output', {1: 'okna_chast1.mp4', 2: 'okna_chast2.mp4', 3: 'poezd_0317.mp4'}[EP])
NFR = int(TOTAL * FPS)


def work(args):
    idx, f0, f1 = args
    scenes = importlib.import_module(SCENES)
    out = os.path.join(BUILD, f'seg_{idx:02d}.mp4')
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    for f in range(f0, f1):
        ctx = cairo.Context(surf)
        scenes.render_frame(ctx, f / FPS)
        surf.flush()
        p.stdin.write(bytes(surf.get_data()))
        if (f - f0) % 150 == 0:
            print(f'seg {idx}: {f - f0}/{f1 - f0}', flush=True)
    p.stdin.close()
    p.wait()
    return out


def main():
    os.makedirs(BUILD, exist_ok=True)
    nseg = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    step = (NFR + nseg - 1) // nseg
    jobs = [(i, i * step, min(NFR, (i + 1) * step)) for i in range(nseg) if i * step < NFR]
    with mp.Pool(os.cpu_count()) as pool:
        segs = pool.map(work, jobs, chunksize=1)
    lst = os.path.join(BUILD, 'segs.txt')
    with open(lst, 'w') as f:
        for s in segs:
            f.write(f"file '{s}'\n")
    video = os.path.join(BUILD, 'video_noaudio.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', video],
                   check=True)
    final = FINAL
    os.makedirs(os.path.dirname(final), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-i', os.path.join(BUILD, 'mix.wav'),
                    '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.0:LRA=11', '-c:a', 'aac', '-b:a', '192k',
                    '-ar', '44100', '-shortest', '-movflags', '+faststart', final], check=True)
    print('done', final)


if __name__ == '__main__':
    main()
