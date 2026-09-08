#!/usr/bin/env python3
"""Convert pinned CC0 visible videos/MCOS labels into leak-safe YOLO splits."""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path
from mcos_decoder import load_groundtruth

CLASS_ID = {"DRONE": 0, "BIRD": 1, "AIRPLANE": 2, "HELICOPTER": 2}

def split_for(index: int) -> str:
    return "train" if index <= 9 else "validation" if index <= 12 else "test"

def dimensions(video: Path) -> tuple[int, int]:
    output = subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","json",str(video)], text=True)
    stream = json.loads(output)["streams"][0]
    return int(stream["width"]), int(stream["height"])

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--source",type=Path,required=True); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--stride",type=int,default=3)
    args=parser.parse_args(); stats={"train":0,"validation":0,"test":0,"objects":{}}
    for video in sorted(args.source.glob("V_*.mp4")):
        parts=video.stem.split("_"); category=parts[1]; index=int(parts[2]); split=split_for(index)
        if index > 15: continue
        labels=load_groundtruth(video.with_name(video.stem+"_LABELS.mat")); width,height=dimensions(video)
        temp=args.output/".frames"/video.stem; temp.mkdir(parents=True,exist_ok=True)
        subprocess.run(["ffmpeg","-loglevel","error","-y","-i",str(video),"-q:v","3",str(temp/"%06d.jpg")],check=True)
        image_dir=args.output/split/"images"; label_dir=args.output/split/"labels"; image_dir.mkdir(parents=True,exist_ok=True); label_dir.mkdir(parents=True,exist_ok=True)
        for frame_index,bbox in enumerate(labels,1):
            if (frame_index-1)%args.stride: continue
            source_frame=temp/f"{frame_index:06d}.jpg"
            if not source_frame.exists(): continue
            name=f"{video.stem}_{frame_index:06d}"; shutil.move(source_frame,image_dir/f"{name}.jpg")
            text=""
            if bbox is not None:
                x,y,w,h=map(float,bbox); xc=(x+w/2)/width; yc=(y+h/2)/height; wn=w/width; hn=h/height
                if 0<=xc<=1 and 0<=yc<=1 and wn>0 and hn>0 and xc-wn/2>=0 and yc-hn/2>=0 and xc+wn/2<=1 and yc+hn/2<=1:
                    text=f"{CLASS_ID[category]} {xc:.8f} {yc:.8f} {wn:.8f} {hn:.8f}\n"; stats["objects"][category]=stats["objects"].get(category,0)+1
            (label_dir/f"{name}.txt").write_text(text,encoding="utf-8"); stats[split]+=1
        shutil.rmtree(temp)
    (args.output/"PREPARATION_REPORT.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(stats)); return 0
if __name__=="__main__": raise SystemExit(main())
