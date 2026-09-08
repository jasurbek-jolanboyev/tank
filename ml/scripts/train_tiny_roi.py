#!/usr/bin/env python3
"""Train a dependency-light fallback ROI classifier using pinned video splits."""
from __future__ import annotations
import argparse, copy, json, random, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

SEED=20260820; NAMES=["drone","bird","aircraft"]
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)

class RoiDataset(Dataset):
    def __init__(self, root: Path, split: str, size: int=96, augment: bool=False):
        self.size=size; self.augment=augment; self.samples=[]
        for label in sorted((root/split/"labels").glob("*.txt")):
            text=label.read_text().strip()
            if text:
                cls,x,y,w,h=text.split(); self.samples.append((root/split/"images"/(label.stem+".jpg"),int(cls),tuple(map(float,(x,y,w,h)))))
    def __len__(self): return len(self.samples)
    def __getitem__(self,index):
        path,cls,(x,y,w,h)=self.samples[index]; image=Image.open(path).convert("RGB"); iw,ih=image.size
        pad=random.uniform(.18,.45) if self.augment else .30
        jx=random.uniform(-.12,.12)*w if self.augment else 0; jy=random.uniform(-.12,.12)*h if self.augment else 0; x+=jx; y+=jy
        left=max(0,(x-w*(.5+pad))*iw); top=max(0,(y-h*(.5+pad))*ih); right=min(iw,(x+w*(.5+pad))*iw); bottom=min(ih,(y+h*(.5+pad))*ih)
        image=image.crop((left,top,right,bottom)).resize((self.size,self.size),Image.Resampling.BILINEAR)
        if self.augment:
            if random.random()<.5: image=ImageOps.mirror(image)
            image=ImageEnhance.Brightness(image).enhance(random.uniform(.65,1.35)); image=ImageEnhance.Contrast(image).enhance(random.uniform(.65,1.4)); image=ImageEnhance.Color(image).enhance(random.uniform(.4,1.4))
        array=np.asarray(image,dtype=np.float32).transpose(2,0,1)/255.0
        return torch.from_numpy(array),cls

class DSBlock(nn.Module):
    def __init__(self,cin,cout,stride=1):
        super().__init__(); self.layers=nn.Sequential(nn.Conv2d(cin,cin,3,stride,1,groups=cin,bias=False),nn.BatchNorm2d(cin),nn.ReLU(),nn.Conv2d(cin,cout,1,bias=False),nn.BatchNorm2d(cout),nn.ReLU())
    def forward(self,x): return self.layers(x)

class TinyRoiClassifier(nn.Module):
    def __init__(self):
        super().__init__(); self.features=nn.Sequential(nn.Conv2d(3,24,3,2,1,bias=False),nn.BatchNorm2d(24),nn.ReLU(),DSBlock(24,32,2),DSBlock(32,48,2),DSBlock(48,72,2),DSBlock(72,96,2),nn.AdaptiveAvgPool2d(1)); self.head=nn.Sequential(nn.Dropout(.2),nn.Linear(96,3))
    def forward(self,x): return self.head(self.features(x).flatten(1))

def evaluate(model,loader):
    model.eval(); matrix=torch.zeros(3,3,dtype=torch.int64); correct=total=0
    with torch.no_grad():
        for images,targets in loader:
            pred=model(images).argmax(1); correct+=int((pred==targets).sum()); total+=len(targets)
            for truth,guess in zip(targets,pred): matrix[int(truth),int(guess)]+=1
    return correct/max(total,1),matrix.tolist()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--data",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--epochs",type=int,default=8); p.add_argument("--batch",type=int,default=32); args=p.parse_args()
    train=RoiDataset(args.data,"train",augment=True); val=RoiDataset(args.data,"validation"); test=RoiDataset(args.data,"test")
    train_loader=DataLoader(train,batch_size=args.batch,shuffle=True,generator=torch.Generator().manual_seed(SEED)); val_loader=DataLoader(val,batch_size=args.batch); test_loader=DataLoader(test,batch_size=args.batch)
    counts=np.bincount([s[1] for s in train.samples],minlength=3); weights=torch.tensor(len(train)/(3*np.maximum(counts,1)),dtype=torch.float32)
    model=TinyRoiClassifier(); optimizer=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4); criterion=nn.CrossEntropyLoss(weight=weights)
    started=time.time(); history=[]; best_accuracy=-1.0; best_state=None
    for epoch in range(args.epochs):
        model.train(); loss_sum=0
        for images,targets in train_loader:
            optimizer.zero_grad(); loss=criterion(model(images),targets); loss.backward(); optimizer.step(); loss_sum+=float(loss)*len(targets)
        val_acc,_=evaluate(model,val_loader); history.append({"epoch":epoch+1,"loss":loss_sum/len(train),"validationAccuracy":val_acc}); print(history[-1],flush=True)
        if val_acc>best_accuracy: best_accuracy=val_acc; best_state=copy.deepcopy(model.state_dict())
    model.load_state_dict(best_state); test_acc,matrix=evaluate(model,test_loader); args.output.mkdir(parents=True,exist_ok=True)
    checkpoint=args.output/"tiny_roi_classifier.pt"; torch.save({"model":model.state_dict(),"classes":NAMES,"inputSize":[96,96],"seed":SEED},checkpoint)
    model.eval(); scripted=torch.jit.trace(model,torch.zeros(1,3,96,96)); scripted.save(str(args.output/"tiny_roi_classifier.torchscript"))
    report={"status":"SMOKE_MODEL_NOT_PRODUCTION","seed":SEED,"classes":NAMES,"trainSamples":len(train),"validationSamples":len(val),"testSamples":len(test),"epochs":args.epochs,"bestValidationAccuracy":best_accuracy,"history":history,"testAccuracy":test_acc,"confusionMatrix":matrix,"trainingSeconds":time.time()-started,"modelBytes":checkpoint.stat().st_size}
    (args.output/"training_report.json").write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report))
if __name__=="__main__": main()
